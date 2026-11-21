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
    rows += vat_rows(f)
    columns = [{"fieldname": "line", "label": _("Reconciling item"), "fieldtype": "Data", "width": 420}, {"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 160}]
    return columns, rows


def vat_rows(f) -> list[dict]:
    """B82 (LDG-212): the 2550Q view. Output VAT per the Sales Journal, per the ledger and per
    the 2550Q returns of the period (Item 37, Total Adjusted Output Tax Due), with the difference."""
    from ph_cas.setup.chart import account_for

    journal = flt(frappe.db.sql(
        """select coalesce(sum(ph_vat_amount), 0) from `tabSales Invoice`
           where company = %s and docstatus = 1 and posting_date between %s and %s""",
        (f.company, f.from_date, f.to_date))[0][0], 2)
    ledger = flt(frappe.db.sql(
        """select coalesce(sum(credit) - sum(debit), 0) from `tabGL Entry`
           where company = %s and is_cancelled = 0 and account = %s and voucher_type = 'Sales Invoice' and posting_date between %s and %s""",
        (f.company, account_for(f.company, "output_vat"), f.from_date, f.to_date))[0][0], 2)
    returns = frappe.get_all("PH Tax Return", filters={"company": f.company, "form": "2550Q", "docstatus": ["<", 2],
                                                       "period_start": [">=", f.from_date], "period_end": ["<=", f.to_date]},
                             fields=["name", "amends", "amended_by"])
    latest = [r.name for r in returns if not r.amended_by]
    on_returns = flt(frappe.db.sql(
        """select coalesce(sum(amount), 0) from `tabPH Tax Return Line` where parent in %s and item in ('37', 'i37')""",
        (tuple(latest) or ("",),))[0][0], 2) if latest else 0
    rows = [
        {"line": _("2550Q: output VAT"), "amount": None, "is_total_row": 1},
        {"line": _("Output VAT per the Sales Journal"), "amount": journal},
        {"line": _("Output VAT credited in the ledger"), "amount": ledger},
        {"line": _("Difference, Sales Journal less ledger (should be zero)"), "amount": flt(journal - ledger, 2)},
    ]
    if latest:
        rows += [
            {"line": _("Output VAT on the 2550Q (Item 37) for this period: {0}").format(", ".join(latest)), "amount": on_returns},
            {"line": _("Difference, Sales Journal less 2550Q (should be zero)"), "amount": flt(journal - on_returns, 2)},
        ]
    else:
        rows.append({"line": _("No 2550Q drafted for a quarter inside these dates yet"), "amount": None})
    return rows
