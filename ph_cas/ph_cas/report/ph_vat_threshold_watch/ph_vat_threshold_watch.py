import frappe
from frappe import _

from ph_cas.tax.vat import company_regime, threshold_status


def execute(filters=None):
    columns = [
        {"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 240},
        {"fieldname": "regime", "label": _("Regime"), "fieldtype": "Data", "width": 90},
        {"fieldname": "gross_12m", "label": _("Gross sales, last 12 months"), "fieldtype": "Currency", "width": 200},
        {"fieldname": "threshold", "label": _("VAT threshold"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 300},
    ]
    rows = []
    for company in frappe.get_all("Company", pluck="name"):
        s = threshold_status(company)
        regime = company_regime(company)
        if s["exceeded"] and regime != "VAT":
            status = _("Over the threshold: VAT registration is required")
        elif s["gross_12m"] > s["threshold"] * 0.8 and regime != "VAT":
            status = _("Within 20% of the threshold")
        else:
            status = _("Below the threshold") if regime != "VAT" else _("VAT-registered")
        rows.append({"company": company, "regime": regime, "gross_12m": s["gross_12m"], "threshold": s["threshold"], "status": status})
    return columns, rows
