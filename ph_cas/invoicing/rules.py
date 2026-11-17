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
    {"fieldname": "ph_cr_atp_no", "fieldtype": "Data", "label": "Collection Receipt ATP number", "depends_on": "ph_use_collection_receipt", "insert_after": "ph_use_collection_receipt",
     "description": "With an ATP the receipt prints its ATP details; without one it prints THIS DOCUMENT IS NOT VALID FOR CLAIM OF INPUT TAX."},
    {"fieldname": "ph_cr_atp_date", "fieldtype": "Date", "label": "Collection Receipt ATP date issued", "depends_on": "ph_cr_atp_no", "insert_after": "ph_cr_atp_no"},
    {"fieldname": "ph_walkin_customer", "fieldtype": "Link", "label": "Walk-in customer for end-of-day invoices", "options": "Customer", "insert_after": "ph_cr_atp_date"},
    {"fieldname": "ph_uses_eis", "fieldtype": "Check", "label": "Issues e-invoices through the BIR EIS", "insert_after": "ph_walkin_customer",
     "description": "Off: every invoice, credit note and debit note also takes the manual invoice number typed by the user, beside the system control number."},
    {"fieldname": "ph_ecommerce", "fieldtype": "Check", "label": "Engaged in e-commerce or internet transactions", "insert_after": "ph_uses_eis",
     "description": "RMC 98-2026: a taxpayer that is not micro and sells through e-commerce or the internet must issue e-invoices through the EIS."},
]

SI_FIELDS = [
    {"fieldname": "ph_end_of_day", "fieldtype": "Check", "label": "End-of-day invoice for small sales", "read_only": 1, "insert_after": "ph_ovc_claim_quarter"},
    {"fieldname": "ph_on_request", "fieldtype": "Check", "label": "Issued on the buyer's request (below the threshold)", "insert_after": "ph_end_of_day"},
    {"fieldname": "ph_manual_invoice_no", "fieldtype": "Data", "label": "Manual invoice number", "insert_after": "naming_series", "in_list_view": 1, "in_standard_filter": 1, "no_copy": 1,
     "description": "Typed by the user before submit (not for companies on the EIS). The BIR serial stays the system control number."},
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


def refuse_cancel(doc, method=None):
    """doc_events['Sales Invoice'].before_cancel: an issued invoice, credit note or
    debit note stays issued (D6 as applied to invoices in B21; LDG-96).

    Issued means it carries a BIR serial. It holds for every role, Administrator
    included; the only escape is the test-site unlock in ph_cas.controls.locks."""
    from ph_cas.controls.locks import locks_active
    from ph_cas.controls.serial import SERIAL_FIELD, document_type_of

    if not doc.get(SERIAL_FIELD) or not locks_active():
        return
    kind = document_type_of(doc) or "Sales Invoice"
    if kind == "Sales Invoice":
        fix = _("Issue a credit note for the full amount (to reverse it) or for the difference, or a debit note or new invoice for an increase.")
    elif kind == "Credit Note":
        fix = _("Issue a debit note to reverse it.")
    else:
        fix = _("Issue a credit note to reverse it.")
    frappe.throw(
        _("{0} {1} (BIR serial {2}) has been issued and cannot be cancelled. {3}").format(_(kind), doc.name, doc.get(SERIAL_FIELD), fix),
        PHLockError,
    )


def eis_required(company: str) -> bool:
    """RMC 98-2026 as the owner reads it: micro taxpayers are exempt; the others
    engaged in e-commerce or internet transactions must issue e-invoices."""
    c = frappe.get_cached_doc("Company", company)
    return bool(c.get("ph_ecommerce")) and (c.get("ph_taxpayer_class") or "Micro") != "Micro"


def warn_eis(doc, method=None):
    """doc_events['Company'].validate: say so when the company must be on the EIS."""
    if doc.get("ph_ecommerce") and (doc.get("ph_taxpayer_class") or "Micro") != "Micro" and not doc.get("ph_uses_eis"):
        frappe.msgprint(_("{0} is not micro and is engaged in e-commerce or internet transactions: it must issue e-invoices through the BIR EIS (RMC 98-2026).").format(doc.name), indicator="orange", alert=True)


def manual_invoice_no_required(doc) -> bool:
    return doc.doctype == "Sales Invoice" and not frappe.get_cached_value("Company", doc.company, "ph_uses_eis")


def validate_manual_invoice_no(doc, method=None):
    """doc_events['Sales Invoice'].before_submit, after the serial: the user types the
    manual invoice number (RDO answer 2); it is unique per company and document type.

    Under the test runner an empty number is filled from the branch and serial so the many
    tests that submit invoices need not type one; tests of this rule set
    frappe.flags.ph_strict_manual_invoice_no."""
    from ph_cas.controls.serial import SERIAL_FIELD, document_type_of

    if not manual_invoice_no_required(doc):
        return
    no = (doc.get("ph_manual_invoice_no") or "").strip()
    if not no and frappe.flags.in_test and not frappe.flags.ph_strict_manual_invoice_no:
        # the branch too: every branch's series starts at 1 (D4)
        no = f"T-{doc.get('ph_branch_code') or ''}-{doc.get(SERIAL_FIELD) or doc.name}"
    if not no:
        frappe.throw(_("Type the manual invoice number before submitting {0}.").format(_(document_type_of(doc) or "Sales Invoice")), title=_("Manual invoice number"))
    doc.ph_manual_invoice_no = no
    kind = document_type_of(doc)
    flags = {"Credit Note": ("is_return", 1), "Debit Note": ("is_debit_note", 1)}
    filters = {"company": doc.company, "docstatus": 1, "ph_manual_invoice_no": no, "name": ("!=", doc.name),
               "is_return": 1 if kind == "Credit Note" else 0}
    if kind != "Credit Note":
        filters["is_debit_note"] = 1 if kind == "Debit Note" else 0
    other = frappe.db.get_value("Sales Invoice", filters, "name")
    if other:
        frappe.throw(_("Manual invoice number {0} is already used on {1}.").format(no, other), title=_("Manual invoice number"))


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
