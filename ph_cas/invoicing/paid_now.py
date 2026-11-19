"""B76 (after ECOUNT's invoice with a bank instead of AR): "Paid in full now" on the Sales Invoice.

For a sale paid in full when it is made (cash, card or transfer at the counter or the office) the
payment is taken on the invoice itself (ERPNext's paid invoice: Is POS with one payment row), so
there is one document: the invoice with its BIR serial. No Payment Entry is made and so no
Collection Receipt serial is used: a collection receipt evidences a collection on account (a
credit sale paid later), while a cash sale is evidenced by the invoice itself (RR 7-2024). The sale
still posts cash or bank in the ledger, so it shows in the Cash Receipts Book under the invoice's
serial, in the cash position, in the Sales Journal and in the 2550Q like any sale.

Refused: a credit or debit note (refund or collect with a Payment Entry), and a customer who
withholds tax (the payment is net of the tax withheld and its 2307 is recorded on a Payment Entry).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import flt

FIELD = "ph_paid_now"
MODE = "ph_paid_mode"


def setup():
    create_custom_fields({"Sales Invoice": [
        {"fieldname": FIELD, "fieldtype": "Check", "label": "Paid in full now", "insert_after": "due_date", "allow_on_submit": 0, "no_copy": 1,
         "description": "The customer pays the whole invoice now. The payment is recorded on the invoice; no collection receipt is issued (the invoice is the evidence of a cash sale)."},
        {"fieldname": MODE, "fieldtype": "Link", "options": "Mode of Payment", "label": "Paid by", "insert_after": FIELD, "default": "Cash", "no_copy": 1,
         "depends_on": f"eval:doc.{FIELD}", "mandatory_depends_on": f"eval:doc.{FIELD}"},
    ]}, ignore_validate=True, update=True)


def _amount(doc) -> float:
    return flt(doc.get("rounded_total") or doc.get("grand_total"), 2)


def before_validate(doc, method=None):
    """Sales Invoice before_validate, after the VAT engine."""
    if not doc.get(FIELD):
        if doc.get("is_pos") and not doc.get("pos_profile"):
            doc.is_pos = 0
            doc.set("payments", [])
        return
    if doc.get("is_return") or doc.get("is_debit_note"):
        frappe.throw(_("A credit or debit note is not paid in full now: refund it, or collect it, with a Payment Entry."), title=_("Paid in full now"))
    mode = doc.get(MODE) or "Cash"
    doc.set(MODE, mode)
    if not _account(mode, doc.company):
        frappe.throw(_("Mode of payment {0} has no account for {1}. Set it on the Mode of Payment (Accounts table).").format(mode, doc.company), title=_("Paid in full now"))
    doc.is_pos = 1
    doc.calculate_taxes_and_totals()
    doc.set("payments", [_row(mode, doc)])


def _account(mode, company):
    return frappe.db.get_value("Mode of Payment Account", {"parent": mode, "company": company}, "default_account")


def _row(mode, doc) -> dict:
    return {"mode_of_payment": mode, "account": _account(mode, doc.company), "type": frappe.get_cached_value("Mode of Payment", mode, "type"),
            "amount": _amount(doc), "base_amount": _amount(doc), "default": 1}


def validate(doc, method=None):
    """Sales Invoice validate, after customer withholding: the payment is the whole invoice."""
    if not doc.get(FIELD):
        return
    if flt(doc.get("ph_wht_total")):
        frappe.throw(_("{0} withholds tax on this invoice: take the payment with a Payment Entry, so the tax withheld and its 2307 are recorded.").format(doc.customer_name or doc.customer),
                     title=_("Paid in full now"))
    amount = _amount(doc)
    if len(doc.payments) != 1 or abs(flt(doc.payments[0].amount) - amount) >= 0.005:
        doc.set("payments", [_row(doc.get(MODE), doc)])
        doc.calculate_taxes_and_totals()
