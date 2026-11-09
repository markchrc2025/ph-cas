"""/pilot: request a 14-day paid pilot or an Enterprise conversation (B37)."""

import frappe

no_cache = 1


def get_context(context):
    context.no_header = 1
    context.product_name = frappe.db.get_single_value("PH CAS Settings", "product_name") or "Sentire Ledger"
    return context
