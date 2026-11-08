"""B16: the optional output VAT credit on uncollected receivables (RR 3-2024)
and the buyer-side reversal of input VAT on unpaid payables. Fields only;
the figures are read by the 2550Q compute."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

SI_FIELDS = [
    {"fieldname": "ph_ovc_section", "fieldtype": "Section Break", "label": "Output VAT credit on uncollected receivable (RR 3-2024)", "insert_after": "ph_wht_rules", "collapsible": 1},
    {"fieldname": "ph_credit_term_days", "fieldtype": "Int", "label": "Agreed credit term (days)", "insert_after": "ph_ovc_section", "description": "Needed to claim the credit: the term must be on the invoice or another written document."},
    {"fieldname": "ph_ovc_claimed", "fieldtype": "Check", "label": "Output VAT credit claimed", "insert_after": "ph_credit_term_days", "allow_on_submit": 1},
    {"fieldname": "ph_ovc_claim_quarter", "fieldtype": "Data", "label": "Claimed in quarter (YYYY-Qn)", "insert_after": "ph_ovc_claimed", "allow_on_submit": 1, "read_only": 1},
]

PI_FIELDS = [
    {"fieldname": "ph_ovc_pi_section", "fieldtype": "Section Break", "label": "Supplier claimed output VAT credit (RR 3-2024)", "insert_after": "ph_rc_rule", "collapsible": 1},
    {"fieldname": "ph_supplier_claimed_ovc", "fieldtype": "Check", "label": "Supplier claimed output VAT credit on this unpaid bill", "insert_after": "ph_ovc_pi_section", "allow_on_submit": 1, "description": "Item 55: the input VAT is reversed this quarter and added back (item 58) when the bill is paid."},
]


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Sales Invoice": SI_FIELDS, "Purchase Invoice": PI_FIELDS}, ignore_validate=True, update=True)


@frappe.whitelist()
def claim_output_vat_credit(sales_invoice: str, quarter_start: str):
    """Mark an invoice's output VAT as claimed for the quarter starting `quarter_start`.
    Allowed only in the quarter after the credit term lapsed, for sales from 27 Apr 2024."""
    from ph_cas.tax.returns import quarter_bounds

    si = frappe.get_doc("Sales Invoice", sales_invoice)
    frappe.has_permission("Sales Invoice", "write", si, throw=True)
    if si.docstatus != 1:
        frappe.throw(_("Only a submitted invoice can be claimed."))
    if getdate(si.posting_date) < getdate("2024-04-27"):
        frappe.throw(_("Only sales from 27 April 2024 qualify (RR 3-2024)."))
    if not si.get("ph_credit_term_days"):
        frappe.throw(_("The invoice has no agreed credit term."))
    if flt(si.outstanding_amount) <= 0:
        frappe.throw(_("The invoice has been collected."))
    if not flt(si.ph_vat_amount):
        frappe.throw(_("The invoice carries no output VAT."))
    lapse = add_days(getdate(si.posting_date), int(si.ph_credit_term_days))
    lapse_q_start, lapse_q_end = quarter_bounds(lapse)
    next_q_start = add_days(lapse_q_end, 1)
    q_start, q_end = quarter_bounds(quarter_start)
    if q_start != next_q_start:
        frappe.throw(_("The credit may be claimed only in the quarter after the term lapsed ({0}).").format(frappe.format(next_q_start, "Date")))
    if si.get("ph_ovc_claimed"):
        frappe.throw(_("Already claimed."))
    si.db_set("ph_ovc_claimed", 1)
    si.db_set("ph_ovc_claim_quarter", f"{q_start.year}-Q{(q_start.month - 1) // 3 + 1}")
    from ph_cas.audit.events import record

    record("posted_edit", "Sales Invoice", si.name, 1, {"ph_ovc_claimed": [0, 1]})
    return si.ph_ovc_claim_quarter
