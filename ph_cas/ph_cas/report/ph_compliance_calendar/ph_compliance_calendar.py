import frappe
from frappe import _

from ph_cas.tax.calendar import calendar


def execute(filters=None):
    f = frappe._dict(filters or {})
    columns = [
        {"fieldname": "form", "label": _("Return"), "fieldtype": "Data", "width": 90},
        {"fieldname": "period_label", "label": _("Period"), "fieldtype": "Data", "width": 90},
        {"fieldname": "period_start", "label": _("From"), "fieldtype": "Date", "width": 100},
        {"fieldname": "period_end", "label": _("To"), "fieldtype": "Date", "width": 100},
        {"fieldname": "due", "label": _("Due"), "fieldtype": "Date", "width": 100},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 220},
        {"fieldname": "figures", "label": _("Figures"), "fieldtype": "Link", "options": "PH Tax Return Figures", "width": 220},
    ]
    return columns, calendar(f.company, int(f.year))
