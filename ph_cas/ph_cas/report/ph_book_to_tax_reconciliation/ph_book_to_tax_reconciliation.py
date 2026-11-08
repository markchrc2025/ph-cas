"""Net income per books to taxable income: the differences, each named."""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.tax.income_tax import _gl_by_class, compute_income_tax


def execute(filters=None):
    f = frappe._dict(filters or {})
    inc = _gl_by_class(f.company, f.from_date, f.to_date, "Income")
    exp = _gl_by_class(f.company, f.from_date, f.to_date, "Expense")
    book_income = flt(sum(inc.values()) - sum(exp.values()), 2)
    fig = {item: amt for item, label, amt, src in compute_income_tax(f.company, f.from_date, f.to_date, annual=True)}
    rows = [
        {"line": _("Net income per books"), "amount": book_income},
        {"line": _("Add: EAR over the cap"), "amount": fig.get("EAR excess", 0)},
        {"line": _("Add: non-deductible expenses"), "amount": fig.get("Non-deductible", 0)},
        {"line": _("Add: income tax expense"), "amount": fig.get("Income tax expense", 0)},
        {"line": _("Add: interest expense disallowed (arbitrage)"), "amount": flt(exp.get("Interest expense", 0) - fig.get("Interest expense", 0), 2) if "Interest expense" in fig else 0},
        {"line": _("Less: income exempt or subjected to final tax"), "amount": -fig.get("Other income", 0)},
        {"line": _("Less: NOLCO applied"), "amount": -fig.get("NOLCO", 0)},
        {"line": _("Taxable income per return"), "amount": fig.get("Taxable income", 0)},
    ]
    explained = flt(sum(r["amount"] for r in rows[:-1]), 2)
    rows.append({"line": _("Unexplained difference (should be zero; OSD explains all of it)"), "amount": flt(fig.get("Taxable income", 0) - explained, 2)})
    columns = [{"fieldname": "line", "label": _("Reconciling item"), "fieldtype": "Data", "width": 420}, {"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 160}]
    return columns, rows
