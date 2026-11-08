"""B22: senior citizen and PWD discounts (RA 9994, RA 10754).

The sale to the holder is VAT-exempt and gets the 20% discount on the
VAT-exclusive price. The invoice shows the gross price, the discount and the
holder's details; the discount is booked to the SC/PWD discount expense
account (deductible from gross income), revenue stays gross. The 5% special
discount on basic necessities (capped weekly) is recorded with its own flag
and carries no VAT exemption.
"""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.setup.chart import account_for
from ph_cas.tax.rules import resolve

DISCOUNT_DESCRIPTION = "Senior Citizen / PWD discount"

SI_FIELDS = [
    {"fieldname": "ph_sc_pwd_section", "fieldtype": "Section Break", "label": "Senior citizen / PWD", "insert_after": "ph_on_request", "collapsible": 1},
    {"fieldname": "ph_sc_pwd_applied", "fieldtype": "Check", "label": "Sale to a senior citizen or PWD (20% discount, VAT-exempt)", "insert_after": "ph_sc_pwd_section"},
    {"fieldname": "ph_sc_pwd_type", "fieldtype": "Select", "label": "Holder", "options": "\nSenior Citizen\nPWD", "insert_after": "ph_sc_pwd_applied", "depends_on": "ph_sc_pwd_applied", "mandatory_depends_on": "ph_sc_pwd_applied"},
    {"fieldname": "ph_sc_pwd_name", "fieldtype": "Data", "label": "Holder's name", "insert_after": "ph_sc_pwd_type", "depends_on": "ph_sc_pwd_applied", "mandatory_depends_on": "ph_sc_pwd_applied"},
    {"fieldname": "ph_sc_pwd_id", "fieldtype": "Data", "label": "OSCA / PWD ID number", "insert_after": "ph_sc_pwd_name", "depends_on": "ph_sc_pwd_applied", "mandatory_depends_on": "ph_sc_pwd_applied"},
    {"fieldname": "ph_sc_pwd_col", "fieldtype": "Column Break", "insert_after": "ph_sc_pwd_id"},
    {"fieldname": "ph_sc_pwd_gross", "fieldtype": "Currency", "label": "Gross price (VAT-exclusive)", "read_only": 1, "insert_after": "ph_sc_pwd_col"},
    {"fieldname": "ph_sc_pwd_discount", "fieldtype": "Currency", "label": "20% discount", "read_only": 1, "insert_after": "ph_sc_pwd_gross"},
    {"fieldname": "ph_sc_pwd_rule", "fieldtype": "Data", "label": "Rule", "read_only": 1, "insert_after": "ph_sc_pwd_discount"},
    {"fieldname": "ph_sc_pwd_special", "fieldtype": "Check", "label": "5% special discount on basic necessities (no VAT exemption, weekly cap)", "insert_after": "ph_sc_pwd_rule"},
]


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Sales Invoice": SI_FIELDS}, ignore_validate=True, update=True)


def before_validate(doc, method=None):
    """doc_events['Sales Invoice'].before_validate, BEFORE ph_cas.tax.vat so the
    lines are exempt when the VAT row is computed."""
    doc.taxes = [t for t in (doc.get("taxes") or []) if (t.get("description") or "") != DISCOUNT_DESCRIPTION]
    doc.ph_sc_pwd_gross = doc.ph_sc_pwd_discount = 0
    doc.ph_sc_pwd_rule = None
    if not doc.get("ph_sc_pwd_applied") and not doc.get("ph_sc_pwd_special"):
        return
    if doc.get("ph_sc_pwd_applied") and doc.get("ph_sc_pwd_special"):
        frappe.throw(_("A sale carries either the 20% discount or the 5% special discount, not both."))
    for f, label in (("ph_sc_pwd_type", _("holder type")), ("ph_sc_pwd_name", _("holder's name")), ("ph_sc_pwd_id", _("OSCA or PWD ID number"))):
        if not (doc.get(f) or "").strip():
            frappe.throw(_("The senior citizen / PWD sale needs the {0} (RR 7-2010, RR 5-2017).").format(label))
    gross = 0.0
    for row in doc.get("items") or []:
        base = flt(row.get("qty")) * flt(row.get("rate"))
        gross += base
        if doc.get("ph_sc_pwd_applied"):
            row.ph_vat_class = "VAT-exempt"
    if doc.get("ph_sc_pwd_applied"):
        rule = resolve("discount", doc.posting_date, discount="sc_pwd")
    else:
        rule = resolve("discount", doc.posting_date, discount="sc_pwd_special")
        cap = flt(rule.threshold)
        if cap and gross > cap:
            frappe.throw(_("The 5% special discount covers purchases up to {0} a week; split or reduce the sale.").format(frappe.format(cap, "Currency")))
    discount = flt(gross * flt(rule.rate) / 100, 2)
    doc.ph_sc_pwd_gross = flt(gross, 2)
    doc.ph_sc_pwd_discount = discount
    doc.ph_sc_pwd_rule = rule.rule_id
    if discount:
        doc.append("taxes", {"charge_type": "Actual", "account_head": account_for(doc.company, "sc_pwd_discount"), "description": DISCOUNT_DESCRIPTION, "tax_amount": -discount, "cost_center": doc.get("cost_center") or frappe.get_cached_value("Company", doc.company, "cost_center")})
