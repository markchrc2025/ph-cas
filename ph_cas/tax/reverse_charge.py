"""B15: reverse-charge VAT.

- Digital services from non-resident providers (RA 12023): the business buyer
  withholds the 12% VAT and remits it on 1600-VT (WV080 private, WV090
  government); a VAT buyer claims it as input VAT, a Non-VAT buyer books it
  as cost.
- Purchases from registered business enterprises (RR 9-2025): the seller's
  invoice leaves the VAT out; the buyer remits it (WV110 on 1600-VT for
  services; goods on 0605 per transaction) and may claim the input VAT only
  after paying it.

Booked as a pair of tax rows that leave the amount due to the supplier
unchanged: Add 12% to the input VAT (or cost) account, Deduct 12% to
Withholding VAT Payable.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from ph_cas.setup.chart import account_for
from ph_cas.tax.rules import resolve

RC_DESCRIPTION_IN = "Reverse-charge VAT (input side)"
RC_DESCRIPTION_OUT = "Reverse-charge VAT payable (1600-VT)"

PI_FIELDS = [
    {"fieldname": "ph_rc_section", "fieldtype": "Section Break", "label": "Reverse-charge VAT", "insert_after": "ph_ewt_period", "collapsible": 1},
    {"fieldname": "ph_rc_kind", "fieldtype": "Select", "label": "Kind", "options": "\nDigital services (non-resident)\nRBE purchase", "read_only": 1, "insert_after": "ph_rc_section"},
    {"fieldname": "ph_rc_atc", "fieldtype": "Data", "label": "ATC", "read_only": 1, "insert_after": "ph_rc_kind"},
    {"fieldname": "ph_rc_base", "fieldtype": "Currency", "label": "Base", "read_only": 1, "insert_after": "ph_rc_atc"},
    {"fieldname": "ph_rc_vat", "fieldtype": "Currency", "label": "VAT to remit", "read_only": 1, "insert_after": "ph_rc_base", "bold": 1},
    {"fieldname": "ph_rc_col", "fieldtype": "Column Break", "insert_after": "ph_rc_vat"},
    {"fieldname": "ph_rc_input_vat", "fieldtype": "Currency", "label": "Input VAT claimable", "read_only": 1, "insert_after": "ph_rc_col"},
    {"fieldname": "ph_rc_claim_after_payment", "fieldtype": "Check", "label": "Claimable only after the VAT is paid (RBE)", "read_only": 1, "insert_after": "ph_rc_input_vat"},
    {"fieldname": "ph_rc_period", "fieldtype": "Data", "label": "1600-VT period (YYYY-MM)", "read_only": 1, "insert_after": "ph_rc_claim_after_payment"},
    {"fieldname": "ph_rc_rule", "fieldtype": "Data", "label": "Rule", "read_only": 1, "insert_after": "ph_rc_period"},
]


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Purchase Invoice": PI_FIELDS}, ignore_validate=True, update=True)


def _clear(doc):
    doc.ph_rc_kind = None
    doc.ph_rc_atc = None
    doc.ph_rc_rule = None
    doc.ph_rc_base = doc.ph_rc_vat = doc.ph_rc_input_vat = 0
    doc.ph_rc_claim_after_payment = 0
    doc.taxes = [t for t in (doc.get("taxes") or []) if (t.get("description") or "") not in (RC_DESCRIPTION_IN, RC_DESCRIPTION_OUT)]


def before_validate(doc, method=None):
    """doc_events['Purchase Invoice'].before_validate, after ph_cas.tax.purchase."""
    _clear(doc)
    supplier = frappe.get_cached_doc("Supplier", doc.supplier)
    company = frappe.get_cached_doc("Company", doc.company)
    date = getdate(doc.posting_date)
    if supplier.get("ph_is_nonresident_dsp"):
        kind, sel = "Digital services (non-resident)", {"supplier": "nonresident_dsp", "payor": "government" if company.get("ph_is_government") else "private"}
    elif supplier.get("ph_is_rbe"):
        kind, sel = "RBE purchase", {"supplier": "rbe"}
    else:
        return
    base = 0.0
    for row in doc.get("items") or []:
        if (row.get("ph_vat_class") or "VATable") in ("VATable", "Government"):
            base += flt(row.get("net_amount")) or flt(row.get("amount")) or flt(row.get("qty")) * flt(row.get("rate"))
    if not base:
        return
    rule = resolve("vat_withholding", date, **sel)
    vat = flt(base * flt(rule.rate) / 100, 2)
    cost_center = doc.get("cost_center") or company.cost_center
    buyer_is_vat = (company.get("ph_vat_status") or "Non-VAT") == "VAT"
    debit_purpose = "input_vat_reverse_charge" if buyer_is_vat else "percentage_tax_expense"
    doc.append("taxes", {"charge_type": "Actual", "add_deduct_tax": "Add", "category": "Total", "account_head": account_for(doc.company, debit_purpose), "description": RC_DESCRIPTION_IN, "tax_amount": vat, "cost_center": cost_center})
    doc.append("taxes", {"charge_type": "Actual", "add_deduct_tax": "Deduct", "category": "Total", "account_head": account_for(doc.company, "wt_vat_payable"), "description": RC_DESCRIPTION_OUT, "tax_amount": vat, "cost_center": cost_center})
    doc.ph_rc_kind = kind
    doc.ph_rc_atc = rule.atc
    doc.ph_rc_base = flt(base, 2)
    doc.ph_rc_vat = vat
    doc.ph_rc_input_vat = vat if buyer_is_vat else 0
    doc.ph_rc_claim_after_payment = 1 if kind == "RBE purchase" else 0
    doc.ph_rc_period = f"{date.year}-{date.month:02d}"
    doc.ph_rc_rule = rule.rule_id
