"""B33: open demo (24-hour access) and paid pilots.

Open demo
- `request_access` (guest API, rate limited) records the request, creates a Demo User
  restricted to its own demo company, and emails a one-click login link valid 24 hours.
- The demo site resets every night (ledger-site reset-demo): the database is restored from
  the golden snapshot taken after the seed, then still-valid demo users are recreated from
  the request log, so a 24-hour promise survives the reset.
- Requests are the lead list. They are appended to a CSV outside the database
  (private/files/demo-requests.csv, which the restore does not touch), mailed to the
  provider, and posted to DEMO_LEADS_WEBHOOK when set (newsletter tool).
- Limits: one demo per email per 30 days, 5 requests per IP per day.

Pilots
- A pilot site is created with `ledger-site new <name> --tier X --pilot DAYS` (pilot_until set,
  demo mode). `daily_pilot_check` disables every user 30 days after pilot_until unless a
  subscription has been recorded, and the monitor reports it. Dropping the site is a
  provider action (ledger-site drop), never automatic.
"""

import csv
import json
import os
import secrets
import urllib.request

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime, today, validate_email_address

DEMO_ROLE = "Demo User"
DEMO_ROLES = ["Accounts User", "Sales User", "Purchase User", "Stock User", "Accounts Manager", "Sales Manager", "Purchase Manager"]
DEMO_HOURS = 24
PER_EMAIL_DAYS = 30
PILOT_GRACE_DAYS = 30
TOKEN_PREFIX = "ph_demo_token:"


def setup():
    """Called from setup_all. Idempotent."""
    if not frappe.db.exists("Role", DEMO_ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": DEMO_ROLE, "desk_access": 1}).insert(ignore_permissions=True)


def is_demo_site() -> bool:
    return bool(frappe.conf.get("ph_demo_site")) and not frappe.conf.get("ph_cas_production")


def _log_path() -> str:
    return frappe.get_site_path("private", "files", "demo-requests.csv")


def _read_log() -> list[dict]:
    p = _log_path()
    if not os.path.exists(p):
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _append_log(row: dict):
    p = _log_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    new = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["requested_on", "expires_on", "email", "full_name", "company", "mobile", "ip", "user", "demo_company"])
        if new:
            w.writeheader()
        w.writerow(row)


def _recent_request(email: str) -> dict | None:
    cutoff = add_days(today(), -PER_EMAIL_DAYS)
    for r in reversed(_read_log()):
        if r["email"].lower() == email.lower() and getdate(r["requested_on"][:10]) >= getdate(cutoff):
            return r
    return None


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=24 * 60 * 60)
def request_access(full_name: str, email: str, company: str = "", mobile: str = "") -> dict:
    """Public signup for the open demo."""
    if not is_demo_site():
        frappe.throw(_("The open demo is not available on this site."), frappe.PermissionError)
    email = (email or "").strip().lower()
    if not validate_email_address(email):
        frappe.throw(_("Please enter a valid email address."))
    full_name = (full_name or "").strip()[:140]
    if not full_name:
        frappe.throw(_("Please enter your name."))
    if not (frappe.flags.mute_emails or frappe.conf.get("mute_emails") or frappe.db.exists("Email Account", {"enable_outgoing": 1})):
        frappe.throw(_("Demo signup is temporarily unavailable (outgoing email is not configured). Please try again later."))
    if _recent_request(email):
        frappe.throw(_("This email already had a demo in the last {0} days. Write to us if you would like a pilot on your own site.").format(PER_EMAIL_DAYS))
    frappe.set_user("Administrator")
    expires = add_to_date(now_datetime(), hours=DEMO_HOURS)
    user, demo_company = _create_demo_user(email, full_name, company)
    token = _issue_token(user, expires)
    row = {
        "requested_on": str(now_datetime())[:19],
        "expires_on": str(expires)[:19],
        "email": email,
        "full_name": full_name,
        "company": (company or "").strip()[:140],
        "mobile": (mobile or "").strip()[:40],
        "ip": frappe.local.request_ip or "",
        "user": user,
        "demo_company": demo_company,
    }
    _append_log(row)
    link = _login_link(token)
    _send_access_mail(email, full_name, link, expires)
    _notify_provider(row)
    _post_webhook(row)
    frappe.db.commit()
    return {"ok": True, "expires_on": str(expires)[:16], "message": _("Check your inbox: your 24-hour demo link is on its way.")}


def _create_demo_user(email: str, full_name: str, company_hint: str) -> tuple[str, str]:
    code = secrets.token_hex(2).upper()
    demo_company = _ensure_demo_company(code, company_hint)
    if frappe.db.exists("User", email):
        u = frappe.get_doc("User", email)
        u.enabled = 1
    else:
        u = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": full_name,
                "enabled": 1,
                "user_type": "System User",
                "send_welcome_email": 0,
                "ph_provider_staff": 1,  # demo seats never count against a tier
            }
        )
    u.set("roles", [{"role": r} for r in [DEMO_ROLE, *DEMO_ROLES]])
    u.flags.ignore_permissions = True
    u.flags.no_welcome_mail = True
    u.save()
    frappe.permissions.add_user_permission("Company", demo_company, email, ignore_permissions=True)
    frappe.defaults.set_user_default("company", demo_company, user=email)
    return u.name, demo_company


def _ensure_demo_company(code: str, hint: str) -> str:
    base = (hint or "").strip()[:40] or "Demo Company"
    name = f"{base} ({code})"
    abbr = f"D{code}"
    if frappe.db.exists("Company", name):
        return name
    co = frappe.get_doc(
        {
            "doctype": "Company",
            "company_name": name,
            "abbr": abbr,
            "default_currency": "PHP",
            "country": "Philippines",
            "chart_of_accounts": "Standard",
            "tax_id": "000-000-000",
            "ph_branch_code": "00000",
            "ph_vat_status": "VAT",
            "ph_registered_name": name.upper(),
        }
    )
    co.flags.ignore_permissions = True
    co.insert()
    from ph_cas.setup.chart import setup_philippine_company

    setup_philippine_company(name)
    return name


def _issue_token(user: str, expires) -> str:
    token = secrets.token_urlsafe(32)
    ttl = int((get_datetime(expires) - now_datetime()).total_seconds())
    frappe.cache().set_value(TOKEN_PREFIX + token, json.dumps({"user": user, "expires": str(expires)}), expires_in_sec=max(ttl, 60))
    return token


def _login_link(token: str) -> str:
    return f"{frappe.utils.get_url()}/demo-login?token={token}"


def consume_token(token: str) -> str | None:
    """Return the user for a valid token (and keep it valid until expiry so the link can be reused within the day)."""
    raw = frappe.cache().get_value(TOKEN_PREFIX + token)
    if not raw:
        return None
    data = json.loads(raw)
    if get_datetime(data["expires"]) < now_datetime():
        frappe.cache().delete_value(TOKEN_PREFIX + token)
        return None
    if not frappe.db.get_value("User", data["user"], "enabled"):
        return None
    return data["user"]


def _muted() -> bool:
    return bool(frappe.flags.mute_emails or frappe.conf.get("mute_emails"))


def _send_access_mail(email: str, full_name: str, link: str, expires):
    if _muted():
        return
    product = frappe.db.get_single_value("PH CAS Settings", "product_name") or "Sentire Ledger"
    frappe.sendmail(
        recipients=[email],
        subject=_("Your {0} demo access (24 hours)").format(product),
        message=f"""<p>Hello {frappe.utils.escape_html(full_name)},</p>
<p>Your demo of {product} is ready. Click the link below to sign in; it works until {str(expires)[:16]} (Manila time), as often as you like.</p>
<p><a href="{link}">{link}</a></p>
<p>What to try: open a Sales Invoice and print it (notice the BIR header and serial number), record a payment with customer withholding, run the 2550Q figures under PH Tax Return Figures, and look at the BIR Audit Trail report.</p>
<p>The demo environment is shared and resets every night at 02:00; nothing you enter is kept. For a pilot on your own site with your own data, reply to this email.</p>
<p>{product}</p>""",
        now=True,
    )


def _notify_provider(row: dict):
    if _muted():
        return
    to = frappe.db.get_value("User", "Administrator", "email")
    if not to or to.endswith("example.com"):
        return
    frappe.sendmail(
        recipients=[to],
        subject=f"Demo request: {row['full_name']} ({row['email']})",
        message="<br>".join(f"<b>{k}</b>: {frappe.utils.escape_html(str(v))}" for k, v in row.items()),
        now=True,
    )


def _post_webhook(row: dict):
    url = frappe.conf.get("demo_leads_webhook") or os.environ.get("DEMO_LEADS_WEBHOOK")
    if not url:
        return
    try:
        req = urllib.request.Request(url, data=json.dumps(row).encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        frappe.log_error("demo leads webhook failed", frappe.get_traceback())


def expire_demo_users():
    """scheduler_events.hourly on the demo site: disable users whose 24 hours are over."""
    if not is_demo_site():
        return 0
    n = 0
    for r in _read_log():
        if get_datetime(r["expires_on"]) < now_datetime() and frappe.db.get_value("User", r["user"], "enabled"):
            if DEMO_ROLE in frappe.get_roles(r["user"]):
                frappe.db.set_value("User", r["user"], "enabled", 0, update_modified=False)
                n += 1
    frappe.db.commit()
    return n


def recreate_active_users():
    """After the nightly restore: give still-valid demo users their access back (new token, new mail)."""
    if not is_demo_site():
        return 0
    frappe.set_user("Administrator")
    n = 0
    for r in _read_log():
        if get_datetime(r["expires_on"]) > now_datetime():
            user, _co = _create_demo_user(r["email"], r["full_name"], r["company"])
            token = _issue_token(user, get_datetime(r["expires_on"]))
            _send_access_mail(r["email"], r["full_name"], _login_link(token), r["expires_on"])
            n += 1
    frappe.db.commit()
    return n


def daily_pilot_check():
    """scheduler_events.daily on every site: a pilot past its grace period is switched off."""
    s = frappe.get_single("PH CAS Settings")
    pilot_until = s.get("pilot_until")
    if not pilot_until or s.get("subscription_until"):
        return {"pilot": False}
    deadline = add_days(getdate(pilot_until), PILOT_GRACE_DAYS)
    if getdate(today()) <= deadline:
        return {"pilot": True, "days_left": (deadline - getdate(today())).days}
    users = frappe.get_all("User", filters={"enabled": 1, "user_type": "System User", "name": ["not in", ("Administrator", "Guest")]}, pluck="name")
    for u in users:
        frappe.db.set_value("User", u, "enabled", 0, update_modified=False)
    frappe.db.commit()
    return {"pilot": True, "days_left": 0, "disabled_users": len(users), "note": "pilot grace period over; provider runs ledger-site drop after export"}


def _pilot_log_path() -> str:
    return frappe.get_site_path("private", "files", "pilot-requests.csv")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=24 * 60 * 60)
def request_pilot(full_name: str, email: str, company: str, mobile: str = "", tier: str = "Team", notes: str = "") -> dict:
    """Public request for a paid pilot or an Enterprise conversation (B37). Logged and mailed to the provider; nothing is created."""
    email = (email or "").strip().lower()
    if not validate_email_address(email):
        frappe.throw(_("Please enter a valid email address."))
    full_name = (full_name or "").strip()[:140]
    company = (company or "").strip()[:140]
    if not full_name or not company:
        frappe.throw(_("Please enter your name and company."))
    row = {
        "requested_on": str(now_datetime())[:19],
        "email": email,
        "full_name": full_name,
        "company": company,
        "mobile": (mobile or "").strip()[:40],
        "tier": tier if tier in ("Solo", "Team", "Business", "Enterprise") else "Team",
        "notes": (notes or "").strip()[:2000].replace("\n", " "),
        "ip": frappe.local.request_ip or "",
    }
    p = _pilot_log_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    new = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new:
            w.writeheader()
        w.writerow(row)
    _notify_provider({"request": "PILOT", **row})
    _post_webhook({"type": "pilot", **row})
    return {"ok": True, "message": _("Thank you. We will write to you within one business day to schedule the pilot.")}
