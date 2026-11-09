"""/demo: open-demo signup page (B33). Posts to ph_cas.hosting.demo_access.request_access."""

import frappe

no_cache = 1


def get_context(context):
    from ph_cas.hosting.demo_access import is_demo_site

    context.no_header = 1
    context.demo_enabled = is_demo_site()
    context.product_name = frappe.db.get_single_value("PH CAS Settings", "product_name") or "Sentire Ledger"
    return context
