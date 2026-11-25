"""B88 (CLD-16): events from Sentire Cloud (sentire.event.v1, signed with the site's event secret)."""

import frappe
from frappe.sentire import verify

from ph_cas.cloud import config

SEEN_PREFIX = "ph_cas:cloud:event:"


@frappe.whitelist(allow_guest=True, methods=["POST"])
def receive():
    body = frappe.request.get_data() or b""
    secret = config.conf().get("event_secret")
    if not config.enabled() or not secret or not verify(body, frappe.get_request_header("X-Sentire-Signature") or "", secret):
        frappe.local.response.http_status_code = 401
        return {"ok": False, "error": "bad signature"}
    event = frappe.parse_json(body.decode("utf-8"))
    if event.get("company") != config.org_id():
        frappe.local.response.http_status_code = 403
        return {"ok": False, "error": "other organization"}
    key = SEEN_PREFIX + str(event.get("id"))
    if frappe.cache().get_value(key):
        return {"ok": True, "duplicate": True}
    handle(event)
    frappe.cache().set_value(key, 1, expires_in_sec=7 * 86400)
    frappe.db.commit()
    return {"ok": True}


def handle(event: dict):
    t = event.get("type")
    data = event.get("data") or {}
    frappe.set_user("Administrator")
    if t == "account.entitlement.changed":
        from ph_cas.cloud.entitlements import apply

        apply(data)
    elif t in ("account.member.removed",):
        from ph_cas.cloud.sso import SUB_FIELD, end_sessions

        name = end_sessions(data.get("userId"))
        if name:
            frappe.db.set_value("User", name, "enabled", 0)
    elif t == "account.sessions.revoked":
        from ph_cas.cloud.sso import end_sessions

        end_sessions(data.get("userId"))
    elif t == "account.member.added":
        from ph_cas.cloud.sso import SUB_FIELD

        name = frappe.db.get_value("User", {SUB_FIELD: data.get("userId")})
        if name:
            frappe.db.set_value("User", name, "enabled", 1)
    # Other account and billing events are informational for Ledger.
