"""B05: the sign-in controls the sworn statement describes (Annex B item 11).

- one session per user; password expiry every 30 days; a strong password
  policy; two-factor sign-in with an OTP app; Frappe's short lock after
  consecutive failures;
- deactivation after N failed sign-ins since the last successful one, N from
  PH CAS Settings (default 5), with an email to System Managers; reactivation
  is an ordinary User edit by a System Manager and is logged by Frappe's
  Version history.
"""

import frappe
from frappe import _

from ph_cas.controls.locks import PHLockError, locks_active

# field: (forced value, comparison). "min" means the stored value must be at
# least this; "max" at most; "eq" exactly.
FORCED_SYSTEM_SETTINGS = {
    "deny_multiple_sessions": (1, "eq"),
    "force_user_to_reset_password": (30, "max_nonzero"),
    "enable_password_policy": (1, "eq"),
    "minimum_password_score": (3, "min"),
    "allow_consecutive_login_attempts": (5, "max_nonzero"),
    "allow_login_after_fail": (300, "min"),
    "enable_two_factor_auth": (1, "eq"),
    "two_factor_method": ("OTP App", "eq"),
    "bypass_2fa_for_retricted_ip_users": (0, "eq"),
    # B80: clients never see Frappe's "New updates are available" popup; Sentire updates every
    # site through a pinned bundle (VERSIONS.md), so the notice would only confuse them
    "disable_system_update_notification": (1, "eq"),
    # B81: no "Switch to Frappe CRM / Helpdesk" ads in the sidebar for System Managers
    "disable_product_suggestion": (1, "eq"),
}


def _ok(value, forced, how) -> bool:
    if how == "eq":
        return (value or 0) == forced if not isinstance(forced, str) else (value or "") == forced
    v = int(value or 0)
    if how == "min":
        return v >= forced
    if how == "max_nonzero":
        return 0 < v <= forced
    return True


def validate_system_settings(doc, method=None):
    """doc_events['System Settings'].validate"""
    if not locks_active():
        return
    for field, (forced, how) in FORCED_SYSTEM_SETTINGS.items():
        if not doc.meta.has_field(field):
            continue
        if not _ok(doc.get(field), forced, how):
            frappe.throw(
                _("System Settings: {0} is fixed by the security baseline (required value: {1}).").format(
                    doc.meta.get_label(field), forced
                ),
                PHLockError,
            )


def force_system_settings():
    """Called from setup_all. Idempotent."""
    settings = frappe.get_doc("System Settings")
    changed = False
    for field, (forced, how) in FORCED_SYSTEM_SETTINGS.items():
        if settings.meta.has_field(field) and not _ok(settings.get(field), forced, how):
            settings.set(field, forced)
            changed = True
    if changed:
        settings.flags.ignore_permissions = True
        settings.flags.ignore_mandatory = True
        settings.save()


def _threshold() -> int:
    n = frappe.db.get_single_value("PH CAS Settings", "failed_signins_before_deactivation")
    return int(n or 5)


def on_activity_log(doc, method=None):
    """doc_events['Activity Log'].after_insert: deactivate after N failures."""
    if not locks_active():
        return
    if doc.get("operation") != "Login" or doc.get("status") != "Failed":
        return
    user = doc.get("user")
    if not user or user in ("Administrator", "Guest") or not frappe.db.exists("User", user):
        return
    last_success = frappe.db.get_value(
        "Activity Log",
        {"user": user, "operation": "Login", "status": "Success"},
        "creation",
        order_by="creation desc",
    )
    filters = {"user": user, "operation": "Login", "status": "Failed"}
    if last_success:
        filters["creation"] = (">", last_success)
    failures = frappe.db.count("Activity Log", filters)
    if failures >= _threshold():
        deactivate(user, failures)


def deactivate(user: str, failures: int):
    if not frappe.db.get_value("User", user, "enabled"):
        return
    frappe.db.set_value("User", user, "enabled", 0)
    frappe.get_doc(
        {
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "User",
            "reference_name": user,
            "content": _("Deactivated by the security baseline after {0} failed sign-ins.").format(failures),
        }
    ).insert(ignore_permissions=True)
    recipients = [
        u["parent"]
        for u in frappe.get_all(
            "Has Role",
            filters={"role": "System Manager", "parenttype": "User"},
            fields=["parent"],
        )
        if u["parent"] not in ("Administrator", user) and frappe.db.get_value("User", u["parent"], "enabled")
    ]
    if recipients:
        try:
            frappe.sendmail(
                recipients=recipients,
                subject=_("User {0} deactivated after failed sign-ins").format(user),
                message=_("{0} was deactivated after {1} failed sign-ins. A System Manager may reactivate the user.").format(
                    user, failures
                ),
                delayed=True,
            )
        except Exception:
            frappe.log_error("ph_cas: deactivation email failed")
