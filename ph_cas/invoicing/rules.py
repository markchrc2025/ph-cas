"""B21: the behaviours around the paper.

- Buyer name, address and TIN are required on a VAT seller's invoice of
  1,000 or more to a VAT-registered buyer (RR 7-2024; rule INV-BUYER-DETAILS-1000).
- A Non-VAT seller issues an invoice for each sale of 500 or more, on request,
  or one end-of-day invoice for the day's smaller sales (INV-NONVAT-500):
  make_end_of_day_invoice builds it.
- Corrections only through credit and debit notes referencing the original
  serial: amending a submitted invoice is refused (D6).
- The Collection Receipt is a per-company switch (RDO question 9 default: on).
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from ph_cas.controls.locks import PHLockError

COMPANY_FIELDS = [
    {"fieldname": "ph_inv_section", "fieldtype": "Section Break", "label": "Invoicing", "insert_after": "ph_corp_small"},
    {"fieldname": "ph_use_collection_receipt", "fieldtype": "Check", "label": "Issue Collection Receipts (supplementary) on customer payments", "default": "1", "insert_after": "ph_inv_section"},
    {"fieldname": "ph_walkin_customer", "fieldtype": "Link", "label": "Walk-in customer for end-of-day invoices", "options": "Customer", "insert_after": "ph_use_collection_receipt"},
]

SI_FIELDS = [
    {"fieldname": "ph_end_of_day", "fieldtype": "Check", "label": "End-of-day invoice for small sales", "read_only": 1, "insert_after": "ph_ovc_claim_quarter"},
    {"fieldname": "ph_on_request", "fieldtype": "Check", "label": "Issued on the buyer's request (below the threshold)", "insert_after": "ph_end_of_day"},
]


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Company": COMPANY_FIELDS, "Sales Invoice": SI_FIELDS}, ignore_validate=True, update=True)


def validate_buyer_details(doc, method=None):
    """doc_events['Sales Invoice'].validate"""
    if doc.get("ph_tax_regime") != "VAT" or doc.get("is_return"):
        return
    customer = frappe.get_cached_doc("Customer", doc.customer)
    if (customer.get("ph_vat_status") or "Non-VAT") != "VAT":
        return
    threshold = flt(frappe.db.get_value("PH Tax Rule", "INV-BUYER-DETAILS-1000", "threshold") or 1000)
    if flt(doc.grand_total) < threshold:
        return
    missing = []
    if not (customer.get("ph_tin") or customer.get("tax_id")):
        missing.append(_("TIN"))
    if not (customer.get("ph_registered_name") or customer.get("customer_name")):
        missing.append(_("registered name"))
    if not (customer.get("ph_address_line1") or doc.get("customer_address") or doc.get("address_display")):
        missing.append(_("address"))
    if missing:
        frappe.throw(
            _("Sales of {0} or more to a VAT-registered buyer need the buyer's {1} on the invoice (RR 7-2024). Complete the customer record.").format(
                frappe.format(threshold, "Currency"), ", ".join(missing)
            ),
            PHLockError,
        )


def refuse_amendment(doc, method=None):
    """doc_events['Sales Invoice'].before_insert: no amendments of issued invoices (D6)."""
    if doc.get("amended_from") and not doc.get("is_return"):
        frappe.throw(
            _("An issued invoice is never amended. Issue a credit note (decrease) or a new invoice (increase) that refers to {0}.").format(doc.amended_from),
            PHLockError,
        )


def collection_receipts_enabled(company: str) -> bool:
    v = frappe.get_cached_value("Company", company, "ph_use_collection_receipt")
    return bool(v) if v is not None else True


@frappe.whitelist()
def make_end_of_day_invoice(company: str, posting_date: str, vatable: float = 0, exempt: float = 0, zero_rated: float = 0, description: str = "Cash sales below the invoicing threshold, end of day"):
    """One invoice for the day's small sales of a Non-VAT seller (or any seller
    that chooses to), to the walk-in customer. Amounts are the day's totals by
    VAT class; the figures come from the cash count or the POS tape."""
    frappe.has_permission("Sales Invoice", "create", throw=True)
    c = frappe.get_cached_doc("Company", company)
    walkin = c.get("ph_walkin_customer")
    if not walkin:
        frappe.throw(_("Set the walk-in customer on the Company first."))
    if getdate(posting_date) != getdate(frappe.utils.nowdate()):
        frappe.throw(_("The end-of-day invoice carries today's date (D5)."))
    threshold = flt(frappe.db.get_value("PH Tax Rule", "INV-NONVAT-500", "threshold") or 500)
    lines = []
    for cls, amount in (("VATable", vatable), ("VAT-exempt", exempt), ("Zero-rated", zero_rated)):
        if flt(amount) > 0:
            lines.append({"item_code": _summary_item(), "item_name": f"{description} ({cls})", "description": f"Individual sales below {threshold:,.0f}", "qty": 1, "rate": flt(amount), "ph_vat_class": cls})
    if not lines:
        frappe.throw(_("Nothing to invoice."))
    si = frappe.get_doc({"doctype": "Sales Invoice", "company": company, "customer": walkin, "posting_date": posting_date, "due_date": posting_date, "items": lines, "ph_end_of_day": 1})
    si.insert()
    return si.name


def _summary_item(code="PH-EOD-SALES"):
    if not frappe.db.exists("Item", code):
        frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": "End-of-day sales summary", "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"), "stock_uom": "Nos", "is_stock_item": 0, "ph_vat_class": "VATable"}).insert(ignore_permissions=True)
    return code
