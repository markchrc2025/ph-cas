"""B20: print counting and the REPRINT rule.

Any server-side render of a submitted Sales Invoice, credit or debit note or
Collection Receipt (print view, PDF, e-mail attachment) is a print. The first
is the original issue; every later one carries REPRINT, its number and the
date of the first print. The count lives in PH Print Record, insert-only.
"""

import frappe
from frappe.utils import now_datetime

COUNTED = ("Sales Invoice", "Payment Entry")


def before_print(doc, method=None, print_settings=None, *args, **kwargs):
    """doc_events['*'].before_print, after the draft refusal."""
    if doc.doctype not in COUNTED or doc.docstatus != 1:
        return
    if doc.doctype == "Payment Entry" and doc.get("payment_type") != "Receive":
        return
    if frappe.flags.get("ph_in_print_preview"):
        return
    last = _last(doc.doctype, doc.name)
    n = int(last.n or 0) + 1
    first = last.first
    frappe.flags.ph_print_record_writer = True
    try:
        rec = frappe.get_doc({"doctype": "PH Print Record", "ref_doctype": doc.doctype, "ref_name": doc.name, "print_no": n, "printed_on": now_datetime(), "printed_by": frappe.session.user, "method": (print_settings or {}).get("method") if isinstance(print_settings, dict) else "print", "copy_type": "original" if n == 1 else "reprint"})
        rec.flags.ignore_permissions = True
        rec.insert()
    finally:
        frappe.flags.ph_print_record_writer = False
    doc.ph_print_no = n
    doc.ph_first_printed_on = first or rec.printed_on
    doc.ph_is_reprint = n > 1


def _last(doctype: str, name: str):
    row = frappe.db.sql(
        "select max(print_no) as n, min(printed_on) as first from `tabPH Print Record` where ref_doctype = %s and ref_name = %s",
        (doctype, name),
        as_dict=True,
    )
    return row[0] if row else frappe._dict(n=0, first=None)


def print_status(doctype: str, name: str) -> dict:
    last = _last(doctype, name)
    return {"prints": int(last.n or 0), "first_printed_on": last.first}


def document_title(doc) -> str:
    if doc.doctype == "Payment Entry":
        return "COLLECTION RECEIPT"
    if doc.get("is_return"):
        return "CREDIT NOTE"
    if doc.get("is_debit_note"):
        return "DEBIT NOTE"
    return "SALES INVOICE"


def company_facts(company: str) -> dict:
    from ph_cas.audit.header import company_facts as facts

    f = facts(company)
    c = frappe.get_cached_doc("Company", company)
    f["business_style"] = c.get("ph_business_style") or ""
    f["accn"] = c.get("ph_accn") or ""
    f["accn_date"] = c.get("ph_accn_date")
    return f


def series_facts(doc) -> dict:
    from ph_cas.controls.serial import document_type_of, series_name

    dt = document_type_of(doc)
    if not dt:
        return {}
    name = series_name(doc.company, doc.get("ph_branch_code") or "00000", dt)
    s = frappe.db.get_value("BIR Series", name, ["prefix", "range_start", "range_end", "accn", "date_issued", "digits"], as_dict=True)
    if not s:
        return {}
    d = int(s.digits or 8)
    return {"range": f"{s.prefix or ''}{int(s.range_start):0{d}d} to {s.prefix or ''}{int(s.range_end):0{d}d}", "accn": s.accn or "", "date_issued": s.date_issued}


def buyer_facts(doc) -> dict:
    if doc.doctype == "Payment Entry":
        party = frappe.get_cached_doc("Customer", doc.party) if doc.party_type == "Customer" else None
    else:
        party = frappe.get_cached_doc("Customer", doc.customer)
    if not party:
        return {}
    tin = party.get("ph_tin") or party.get("tax_id") or ""
    branch = party.get("ph_branch_code") or "00000"
    address = ", ".join(p for p in [party.get("ph_address_line1"), party.get("ph_address_line2"), party.get("ph_zip")] if p)
    if not address and doc.get("address_display"):
        address = frappe.utils.strip_html(doc.address_display).replace("\n", ", ")
    return {"name": party.get("ph_registered_name") or party.get("customer_name") or party.name, "tin": f"{tin}-{branch}" if tin else "", "address": address, "vat_status": party.get("ph_vat_status") or ""}
