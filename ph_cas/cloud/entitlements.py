"""B88 (CLD-16, task 4.3): Ledger's plan, limits and access come from Sentire Cloud.

The entitlement is applied to PH CAS Settings (tier and limits), so the existing B32 checks keep working;
the PH Subscription record and `ledger-site set-tier` become a mirror on Sentire Cloud sites.
State READ_ONLY (unpaid, day 8 of dunning) refuses every change; reading stays open.
"""

import frappe
from frappe import _
from frappe.utils import add_days, today

from ph_cas.cloud import config

PLAN_TIER = {"solo": "Solo", "team": "Team", "business": "Business", "enterprise": "Enterprise"}
LIMIT_FIELD = {"users": "max_users", "companies": "max_companies", "branches": "max_branches", "invoices_per_month": "monthly_invoice_limit"}
STATE_KEY = "ph_cas:cloud:state"


class PaymentRequired(frappe.ValidationError):
    """HTTP 402 PAYMENT_REQUIRED (System Design NFR-18)."""

    http_status_code = 402


def apply(ent: dict) -> dict:
    """Write an entitlement (the Sentire Cloud JSON) to PH CAS Settings. Older versions are ignored."""
    s = frappe.get_single("PH CAS Settings")
    current = state()
    if int(ent.get("version") or 0) < int(current.get("version") or 0):
        return current
    tier = PLAN_TIER.get(ent.get("plan") or "", s.subscription_tier or "Solo")
    values = {"subscription_tier": tier}
    for key, field in LIMIT_FIELD.items():
        lim = (ent.get("limits") or {}).get(key)
        values[field] = 0 if not lim or lim.get("value") is None else int(lim["value"])
    st = ent.get("state") or "OFF"
    # subscription_until drives the existing expiry banner; the paid period end is the truth.
    values["subscription_until"] = ent.get("periodEnd") if st == "ACTIVE" else add_days(today(), -1)
    for k, v in values.items():
        s.set(k, v)
    s.flags.ignore_permissions = True
    s.flags.from_sentire_cloud = True
    s.save()
    out = {"state": st, "version": int(ent.get("version") or 0), "features": [f.get("key") if isinstance(f, dict) else f for f in ent.get("features") or []], "plan": ent.get("plan")}
    frappe.cache().set_value(STATE_KEY, out)
    frappe.db.set_default("ph_cas_cloud_state", frappe.as_json(out))
    return out


def state() -> dict:
    cached = frappe.cache().get_value(STATE_KEY)
    if cached:
        return cached
    raw = frappe.db.get_default("ph_cas_cloud_state")
    out = frappe.parse_json(raw) if raw else {}
    if out:
        frappe.cache().set_value(STATE_KEY, out)
    return out


def has_feature(key: str) -> bool:
    return key in (state().get("features") or [])


def pull():
    """Hourly, and after an outage: read the entitlement with Ledger's machine token (FR-25)."""
    if not config.enabled():
        return
    from ph_cas.cloud.client import get

    try:
        ent = get(f"/api/v1/entitlements/{config.org_id()}/ledger")
    except Exception:
        # Apps fail safe (NFR-02): keep the last known entitlement.
        frappe.log_error("Sentire Cloud: entitlement not refreshed")
        return
    apply(ent)
    frappe.db.commit()


EXEMPT = {"PH CAS Settings", "Access Log", "Activity Log", "Error Log", "Version", "Comment", "Email Queue", "Session Default Settings", "Route History", "PH Event Log", "Scheduled Job Log", "Deleted Document"}


def refuse_when_read_only(doc, method=None):
    """doc_events['*'] validate, before_submit, before_cancel and on_trash: no changes while the subscription is read-only."""
    if not config.enabled() or frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_test:
        return
    if doc.doctype in EXEMPT or frappe.session.user == "Administrator":
        return
    if state().get("state") in ("READ_ONLY", "OFF"):
        raise_payment_required(
            "subscription",
            _("Your Sentire Ledger subscription is read-only because a billing statement is unpaid. Your Owner can pay it in Sentire Cloud; access returns at once."),
            return_path="/app",
            billing=True,
        )


def raise_payment_required(feature: str, message: str, return_path: str = "/app", billing: bool = False):
    url = f"{config.issuer()}/org/billing" if billing else config.upgrade_url(feature, return_path)
    frappe.local.response["sentire_paywall"] = {"code": "PAYMENT_REQUIRED", "feature": feature, "upgradeUrl": url}
    frappe.throw(
        message + f'<br><br><a class="btn btn-primary btn-sm" href="{url}">' + (_("Open billing") if billing else _("See how to unlock this")) + "</a>",
        PaymentRequired,
        title=_("Subscription"),
    )
