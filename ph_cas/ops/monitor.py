"""B31: what the operator watches: site up, backup age, chain check, disk,
scheduler, draft rules on a production site."""

import os
import shutil

import frappe

from ph_cas.branding import product_name
from frappe.utils import get_datetime, now_datetime, time_diff_in_hours


@frappe.whitelist()
def status() -> dict:
    s = frappe.get_single("PH CAS Settings")
    last_backup = s.get("last_backup_on")
    backup_age_h = time_diff_in_hours(now_datetime(), get_datetime(last_backup)) if last_backup else None
    total, used, free = shutil.disk_usage(frappe.get_site_path())
    from ph_cas.tax.rules import draft_rules
    from ph_cas.controls.locks import is_production_site

    drafts = len(draft_rules())
    checks = {
        "site": frappe.local.site,
        "production": is_production_site(),
        "scheduler_enabled": not frappe.utils.scheduler.is_scheduler_disabled(verbose=False) if hasattr(frappe.utils, "scheduler") else None,
        "last_backup_on": str(last_backup) if last_backup else None,
        "backup_age_hours": round(backup_age_h, 1) if backup_age_h is not None else None,
        "backup_ok": backup_age_h is not None and backup_age_h <= 26,
        "last_chain_check": str(s.get("last_chain_check")) if s.get("last_chain_check") else None,
        "chain_ok": bool(s.get("last_chain_check_ok")),
        "disk_free_gb": round(free / 1e9, 2),
        "disk_ok": free / total > 0.15,
        "draft_rules": drafts,
        "draft_rules_ok": not (is_production_site() and drafts),
    }
    from ph_cas.hosting.tiers import check_subscription_status

    checks["subscription"] = check_subscription_status()  # B32: informational, never fails the site
    checks["ok"] = all(checks[k] for k in ("backup_ok", "chain_ok", "disk_ok", "draft_rules_ok"))
    return checks


def alert_if_needed():
    """scheduler_events.hourly: email System Managers when a check fails."""
    st = status()
    failed = [k for k in ("backup_ok", "chain_ok", "disk_ok", "draft_rules_ok") if not st[k]]
    if not failed:
        return st
    recipients = [u["parent"] for u in frappe.get_all("Has Role", filters={"role": "System Manager", "parenttype": "User"}, fields=["parent"]) if u["parent"] != "Administrator" and frappe.db.get_value("User", u["parent"], "enabled")]
    if recipients:
        frappe.sendmail(recipients=recipients, subject=f"{product_name()} {st['site']}: checks failing ({', '.join(failed)})", message=frappe.as_json(st))
    return st
