"""The record of SC/PWD sales the law requires: holder, ID, date, invoice, gross and discount."""

import frappe
from frappe import _


def execute(filters=None):
    f = frappe._dict(filters or {})
    columns = [
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
        {"fieldname": "bir_serial", "label": _("Invoice No."), "fieldtype": "Data", "width": 120},
        {"fieldname": "name", "label": _("Document"), "fieldtype": "Link", "options": "Sales Invoice", "width": 160},
        {"fieldname": "ph_sc_pwd_type", "label": _("Holder"), "fieldtype": "Data", "width": 110},
        {"fieldname": "ph_sc_pwd_name", "label": _("Name"), "fieldtype": "Data", "width": 200},
        {"fieldname": "ph_sc_pwd_id", "label": _("OSCA / PWD ID"), "fieldtype": "Data", "width": 130},
        {"fieldname": "ph_sc_pwd_gross", "label": _("Gross (VAT-exclusive)"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "ph_sc_pwd_discount", "label": _("Discount"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "kind", "label": _("Kind"), "fieldtype": "Data", "width": 90},
    ]
    rows = frappe.get_all(
        "Sales Invoice",
        filters={"company": f.company, "docstatus": 1, "posting_date": ("between", [f.from_date, f.to_date]), "ph_sc_pwd_discount": (">", 0)},
        fields=["posting_date", "bir_serial", "name", "ph_sc_pwd_type", "ph_sc_pwd_name", "ph_sc_pwd_id", "ph_sc_pwd_gross", "ph_sc_pwd_discount", "ph_sc_pwd_special"],
        order_by="posting_date, bir_serial",
    )
    for r in rows:
        r["kind"] = "5% special" if r.pop("ph_sc_pwd_special") else "20%"
    return columns, rows
