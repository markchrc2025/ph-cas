"""Tax withheld by customers (booked on payments) against the 2307s received,
per customer and quarter. The difference is what to chase."""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.ph_cas.doctype.ph_2307_received.ph_2307_received import quarter_of


def execute(filters=None):
    f = frappe._dict(filters or {})
    columns = [
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 240},
        {"fieldname": "quarter", "label": _("Quarter"), "fieldtype": "Data", "width": 90},
        {"fieldname": "withheld", "label": _("Withheld on payments"), "fieldtype": "Currency", "width": 170},
        {"fieldname": "certified", "label": _("Per 2307s received"), "fieldtype": "Currency", "width": 170},
        {"fieldname": "difference", "label": _("Not yet certified"), "fieldtype": "Currency", "width": 160},
    ]
    withheld = {}
    for r in frappe.db.sql(
        """select p.party as customer, p.posting_date, d.amount from `tabPayment Entry Deduction` d
           join `tabPayment Entry` p on p.name = d.parent
           where p.docstatus = 1 and p.company = %(company)s and p.party_type = 'Customer'
             and p.posting_date between %(from_date)s and %(to_date)s and d.description like 'Withheld by customer%%'""",
        f,
        as_dict=True,
    ):
        key = (r.customer, quarter_of(r.posting_date))
        withheld[key] = withheld.get(key, 0.0) + flt(r.amount)
    certified = {}
    for r in frappe.get_all(
        "PH 2307 Received",
        filters={"company": f.company, "docstatus": 1, "period_from": (">=", f.from_date), "period_to": ("<=", f.to_date)},
        fields=["customer", "quarter", "total_tax"],
    ):
        key = (r.customer, r.quarter)
        certified[key] = certified.get(key, 0.0) + flt(r.total_tax)
    rows = []
    for key in sorted(set(withheld) | set(certified)):
        w, c = withheld.get(key, 0.0), certified.get(key, 0.0)
        rows.append({"customer": key[0], "quarter": key[1], "withheld": w, "certified": c, "difference": flt(w - c, 2)})
    return columns, rows
