"""Container-time configuration from environment variables (run at every start by
deploy/entrypoint.sh: bench --site <site> execute ph_cas.deploy_config.apply).

Outgoing email (for the two-factor QR/OTP mails, password resets, notifications):
  SMTP_HOST            SMTP server (e.g. your Postal server)
  SMTP_PORT            default 587
  SMTP_USER            SMTP login (alias: SEED_USER)
  SMTP_PASSWORD        SMTP password (alias: SEED_PASSWORD)
  SMTP_FROM            sender address, e.g. cas@yourdomain.ph (default: SMTP_USER if it is an address)
  SMTP_FROM_NAME       sender display name (default: PH CAS)
  SMTP_TLS             1 = STARTTLS (default), 0 = plain; SMTP_SSL=1 for implicit TLS (port 465)
Administrator account:
  ADMIN_EMAIL          mailbox of the Administrator user (where its 2FA mails go)
  ADMIN_PASSWORD       re-applied at every start, so the Dokploy value is always the one that works
Branding (PH CAS Settings, shown on the BIR header of every print and export):
  PRODUCT_NAME         e.g. Sentire Ledger
  PROVIDER_NAME        e.g. MCRC Tax and Accounting Services
Demo convenience (ignored when ph_cas_production is 1):
  PH_2FA               0 turns two-factor sign-in off on a demo site until email works
All values are read from the environment only; nothing is logged.
"""

import os

import frappe


def _env(*names, default=None):
    for n in names:
        v = os.environ.get(n)
        if v not in (None, ""):
            return v
    return default


def apply():
    """Primary site (SITE_NAME): everything, including the Administrator account and the demo switches."""
    frappe.set_user("Administrator")
    out = []
    out.append(_email_account())
    out.append(_admin_email())
    out.append(_admin_password())
    out.append(_two_factor())
    out.append(_branding())
    frappe.db.commit()
    return "; ".join(x for x in out if x)


def apply_shared():
    """Client sites on a multi-site container: shared outgoing email and branding only.
    Their Administrator password and two-factor setting are their own."""
    frappe.set_user("Administrator")
    out = [_email_account(), _branding()]
    frappe.db.commit()
    return "; ".join(x for x in out if x)


def _email_account():
    host = _env("SMTP_HOST")
    if not host:
        return "smtp: SMTP_HOST not set, outgoing email not configured"
    user = _env("SMTP_USER", "SEED_USER")
    password = _env("SMTP_PASSWORD", "SEED_PASSWORD")
    sender = _env("SMTP_FROM", default=user if user and "@" in user else None)
    if not sender:
        return "smtp: SMTP_FROM not set (and SMTP_USER is not an address), skipped"
    name = "Outgoing (SMTP)"
    values = {
        "email_account_name": name,
        "email_id": sender,
        "service": "",
        "enable_incoming": 0,
        "enable_outgoing": 1,
        "default_outgoing": 1,
        "always_use_account_email_id_as_sender": 1,
        "always_use_account_name_as_sender_name": 1,
        "smtp_server": host,
        "smtp_port": int(_env("SMTP_PORT", default="587")),
        "use_tls": 1 if _env("SMTP_TLS", default="1") == "1" else 0,
        "use_ssl_for_outgoing": 1 if _env("SMTP_SSL", default="0") == "1" else 0,
        "no_smtp_authentication": 0 if user else 1,
        "login_id_is_different": 1 if user and user != sender else 0,
        "login_id": user if user and user != sender else None,
        "awaiting_password": 0,
    }
    if frappe.db.exists("Email Account", name):
        doc = frappe.get_doc("Email Account", name)
    else:
        doc = frappe.new_doc("Email Account")
    doc.update(values)
    if password:
        doc.password = password
    doc.flags.ignore_permissions = True
    try:
        doc.save()
    except Exception as e:  # noqa: BLE001 - SMTP connection check failed; report, do not crash the start
        frappe.db.rollback()
        detail = " | ".join(
            [str(e)] + [str(m.get("message") if isinstance(m, dict) else m) for m in (frappe.get_message_log() or [])]
        )
        if password:
            detail = detail.replace(password, "***")
        return (
            f"smtp: Email Account not saved ({type(e).__name__}: {detail[:300]}); "
            f"host {host} port {values['smtp_port']} tls {values['use_tls']} ssl {values['use_ssl_for_outgoing']} "
            f"user {'set' if user else 'none'} password {'set' if password else 'MISSING'}"
        )
    # other accounts must not stay default outgoing
    frappe.db.sql("update `tabEmail Account` set default_outgoing=0 where name!=%s", name)
    frappe.db.set_single_value("System Settings", "email_footer_address", _env("SMTP_FROM_NAME", default="PH CAS"))
    return f"smtp: outgoing email via {host}"


def _admin_email():
    email = _env("ADMIN_EMAIL")
    if not email:
        return ""
    if frappe.db.get_value("User", "Administrator", "email") != email:
        frappe.db.set_value("User", "Administrator", {"email": email}, update_modified=False)
        frappe.clear_cache(user="Administrator")
    return "admin email set"


def _two_factor():
    if frappe.conf.get("ph_cas_production"):
        return ""
    if _env("PH_2FA", default="1") == "0":
        frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 0)
        frappe.clear_cache()
        return "demo: two-factor sign-in OFF (PH_2FA=0)"
    frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 1)
    return ""


def _branding():
    product = _env("PRODUCT_NAME")
    provider = _env("PROVIDER_NAME")
    if not product and not provider:
        return ""
    s = frappe.get_single("PH CAS Settings")
    changed = False
    if product and s.get("product_name") != product:
        s.product_name = product
        changed = True
    if provider and s.get("provider_name") != provider:
        s.provider_name = provider
        changed = True
    if changed:
        s.flags.ignore_permissions = True
        s.save()
    frappe.db.set_single_value("System Settings", "app_name", product or s.product_name)
    return f"branding: {s.product_name}"


def _admin_password():
    pw = _env("ADMIN_PASSWORD")
    if not pw:
        return ""
    from frappe.utils.password import check_password, update_password

    try:
        check_password("Administrator", pw)
        return ""
    except frappe.AuthenticationError:
        update_password("Administrator", pw, logout_all_sessions=False)
        return "admin password re-applied"
