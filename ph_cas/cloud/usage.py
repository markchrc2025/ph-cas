"""B88 (CLD-16, task 4.5): daily usage report to Sentire Cloud (FR-26)."""

import frappe
from frappe.utils import today

from ph_cas.cloud import config


def report():
    if not config.enabled():
        return
    from ph_cas.cloud.client import post
    from ph_cas.hosting.tiers import usage

    u = usage()
    day = today()
    items = [
        {"organizationId": config.org_id(), "appId": "ledger", "meter": meter, "quantity": int(qty), "periodDate": str(day), "idempotencyKey": f"{day}:{meter}"}
        for meter, qty in (("users", u["users"]), ("companies", u["companies"]), ("branches", u["branches"]), ("invoices_per_month", u["invoices_this_month"]))
    ]
    try:
        post("/api/v1/usage", items)
    except Exception:
        frappe.log_error("Sentire Cloud: usage not reported")
