"""B18: income tax figures (1701Q, 1702Q, 1701, 1701A, 1702-RT), MCIT,
deduction caps, NOLCO and the book-to-tax reconciliation.

The computes read the General Ledger by account root type and the account's
tax class (a field added to Account), the company's income-tax options, PH
2307 Received income-tax lines, earlier quarters' figures and PH NOLCO.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from ph_cas.tax.rules import resolve

TAX_CLASS_OPTIONS = "\nOrdinary\nEntertainment, amusement and recreation\nInterest expense\nNon-deductible\nIncome tax expense\nInterest income subject to final tax\nExempt or final-taxed income\nCost of sales"

ACCOUNT_FIELDS = [
    {"fieldname": "ph_tax_class", "fieldtype": "Select", "label": "Tax class (income tax)", "options": TAX_CLASS_OPTIONS, "insert_after": "account_type", "description": "How this account enters taxable income. Blank means Ordinary for expenses and taxable for income."},
]

COMPANY_FIELDS = [
    {"fieldname": "ph_it_section", "fieldtype": "Section Break", "label": "Income tax options", "insert_after": "ph_accn_date"},
    {"fieldname": "ph_income_tax_option", "fieldtype": "Select", "label": "Income tax", "options": "Corporate\nGraduated (individual)\n8% option (individual)", "default": "Corporate", "insert_after": "ph_it_section"},
    {"fieldname": "ph_deduction_method", "fieldtype": "Select", "label": "Deductions", "options": "Itemized\nOSD (40%)", "default": "Itemized", "insert_after": "ph_income_tax_option"},
    {"fieldname": "ph_mixed_income", "fieldtype": "Check", "label": "Mixed-income earner (8% without the 250,000 reduction)", "insert_after": "ph_deduction_method"},
    {"fieldname": "ph_it_col", "fieldtype": "Column Break", "insert_after": "ph_mixed_income"},
    {"fieldname": "ph_primary_business", "fieldtype": "Select", "label": "Primary business (EAR cap)", "options": "Services\nGoods", "default": "Services", "insert_after": "ph_it_col"},
    {"fieldname": "ph_operations_start_year", "fieldtype": "Int", "label": "Year operations began (MCIT from the 4th year after)", "insert_after": "ph_primary_business"},
    {"fieldname": "ph_corp_small", "fieldtype": "Check", "label": "Net taxable income up to 5M and total assets up to 100M (20% rate)", "insert_after": "ph_operations_start_year"},
]

GRADUATED_2023 = [  # (upper bound, rate, fixed tax at lower bound, lower bound)
    (250000, 0, 0, 0),
    (400000, 15, 0, 250000),
    (800000, 20, 22500, 400000),
    (2000000, 25, 102500, 800000),
    (8000000, 30, 402500, 2000000),
    (None, 35, 2202500, 8000000),
]


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Account": ACCOUNT_FIELDS, "Company": COMPANY_FIELDS}, ignore_validate=True, update=True)
    # cost of sales accounts of the Standard chart
    for name in frappe.get_all("Account", filters={"account_type": "Cost of Goods Sold", "ph_tax_class": ("in", ["", None])}, pluck="name"):
        frappe.db.set_value("Account", name, "ph_tax_class", "Cost of sales", update_modified=False)


def _gl_by_class(company, start, end, root_type) -> dict:
    """{tax_class: amount} with income as credit less debit and expense as debit less credit."""
    rows = frappe.db.sql(
        """select ifnull(a.ph_tax_class, '') as cls, a.account_type,
                  sum(g.credit) - sum(g.debit) as cr, sum(g.debit) - sum(g.credit) as dr
           from `tabGL Entry` g join `tabAccount` a on a.name = g.account
           where g.company = %s and g.is_cancelled = 0 and g.posting_date between %s and %s
             and a.root_type = %s and g.voucher_type != 'Period Closing Voucher'
           group by cls, a.account_type""",
        (company, start, end, root_type),
        as_dict=True,
    )
    out = {}
    for r in rows:
        cls = r.cls or ("Cost of sales" if r.account_type == "Cost of Goods Sold" and root_type == "Expense" else "Ordinary")
        out[cls] = out.get(cls, 0.0) + flt(r.cr if root_type == "Income" else r.dr)
    return out


def graduated_tax(taxable: float) -> float:
    if taxable <= 0:
        return 0.0
    for upper, rate, fixed, lower in GRADUATED_2023:
        if upper is None or taxable <= upper:
            return flt(fixed + (taxable - lower) * rate / 100, 2)
    return 0.0


def _credits_2307(company, start, end) -> float:
    rows = frappe.db.sql(
        """select coalesce(sum(l.tax_withheld), 0) from `tabPH 2307 Received Line` l
           join `tabPH 2307 Received` d on d.name = l.parent
           where d.docstatus = 1 and d.company = %s and l.kind = 'Income tax' and d.period_from >= %s and d.period_to <= %s""",
        (company, start, end),
    )
    return flt(rows[0][0], 2)


def _prior_quarters_tax(company, form_q, year, before_start) -> float:
    rows = frappe.get_all("PH Tax Return Figures", filters={"company": company, "form": form_q, "period_start": (">=", f"{year}-01-01"), "period_end": ("<", before_start)}, pluck="name")
    total = 0.0
    for name in rows:
        total += frappe.get_doc("PH Tax Return Figures", name).figure("Tax due")
    return flt(total, 2)


def _nolco_available(company, year) -> list:
    return frappe.get_all("PH NOLCO", filters={"company": company, "expiry_year": (">=", year), "loss_year": ("<", year), "balance": (">", 0)}, fields=["name", "balance", "loss_year"], order_by="loss_year")


def compute_income_tax(company: str, start, end, annual: bool) -> list:
    c = frappe.get_cached_doc("Company", company)
    year = getdate(start).year
    cumulative_start = f"{year}-01-01" if not annual else start  # quarterly returns are cumulative for the year
    inc = _gl_by_class(company, cumulative_start, end, "Income")
    exp = _gl_by_class(company, cumulative_start, end, "Expense")

    sales = flt(sum(v for k, v in inc.items() if k not in ("Exempt or final-taxed income", "Interest income subject to final tax")), 2)
    final_taxed_interest = flt(inc.get("Interest income subject to final tax", 0), 2)
    exempt_income = flt(inc.get("Exempt or final-taxed income", 0), 2)
    cogs = flt(exp.get("Cost of sales", 0), 2)
    gross_income = flt(sales - cogs, 2)

    option = c.get("ph_income_tax_option") or "Corporate"
    method = c.get("ph_deduction_method") or "Itemized"
    L = [
        ("Sales", "Sales/Revenues/Receipts/Fees", sales, "computed"),
        ("COGS", "Less: Cost of Sales/Services", cogs, "computed"),
        ("Gross income", "Gross Income from Operation", gross_income, "computed"),
        ("Other income", "Income exempt or subjected to final tax (excluded)", flt(exempt_income + final_taxed_interest, 2), "computed"),
    ]

    if option == "8% option (individual)":
        rule = resolve("income", end, taxpayer="individual", option="8pct", mixed="1" if c.get("ph_mixed_income") else "0")
        reduction = 0.0 if c.get("ph_mixed_income") else 250000.0
        base = max(flt(sales - reduction, 2), 0.0)
        tax_due = flt(base * flt(rule.rate) / 100, 2)
        L += [("Base", f"Gross sales less {reduction:,.0f} reduction", base, "computed"), ("Rate", f"Rate % ({rule.rule_id})", flt(rule.rate), "computed"), ("Taxable income", "Not applicable under the 8% option", 0.0, "computed")]
    else:
        # deductions
        ear_total = flt(exp.get("Entertainment, amusement and recreation", 0), 2)
        interest_exp = flt(exp.get("Interest expense", 0), 2)
        ordinary = flt(exp.get("Ordinary", 0), 2)
        non_deductible = flt(exp.get("Non-deductible", 0), 2)
        income_tax_exp = flt(exp.get("Income tax expense", 0), 2)
        if method == "OSD (40%)":
            osd = resolve("income", end, deduction="osd")
            osd_base = sales if option != "Corporate" else gross_income
            deductions = flt(osd_base * flt(osd.rate) / 100, 2)
            L += [("Deductions", f"Optional Standard Deduction {flt(osd.rate):g}% of {'gross sales' if option != 'Corporate' else 'gross income'} ({osd.rule_id})", deductions, "computed")]
            ear_excess = interest_reduction = 0.0
        else:
            ear_cap_rule = resolve("cap", end, ear="goods" if (c.get("ph_primary_business") == "Goods") else "services")
            ear_cap = flt(sales * flt(ear_cap_rule.rate) / 100, 2)
            ear_allowed = min(ear_total, ear_cap)
            ear_excess = flt(ear_total - ear_allowed, 2)
            arb = resolve("cap", end, base="interest_income_final_tax")
            interest_reduction = flt(final_taxed_interest * flt(arb.rate) / 100, 2)
            interest_allowed = max(flt(interest_exp - interest_reduction, 2), 0.0)
            deductions = flt(ordinary + ear_allowed + interest_allowed, 2)
            L += [
                ("Ordinary deductions", "Ordinary and necessary expenses", ordinary, "computed"),
                ("EAR", f"Entertainment, amusement and recreation (cap {flt(ear_cap_rule.rate):g}% = {ear_cap:,.2f})", ear_allowed, "computed"),
                ("EAR excess", "EAR over the cap (added back)", ear_excess, "computed"),
                ("Interest expense", f"Interest expense less {flt(arb.rate):g}% of interest income subjected to final tax ({interest_reduction:,.2f})", interest_allowed, "computed"),
                ("Non-deductible", "Non-deductible expenses (added back)", non_deductible, "computed"),
                ("Income tax expense", "Income tax expense (added back)", income_tax_exp, "computed"),
                ("Deductions", "Total Allowable Itemized Deductions", deductions, "computed"),
            ]
        net_before_nolco = flt(gross_income - deductions, 2)
        nolco_used = 0.0
        if method != "OSD (40%)" and net_before_nolco > 0 and annual:
            remaining = net_before_nolco
            for n in _nolco_available(company, year):
                take = min(flt(n.balance), remaining)
                if take <= 0:
                    continue
                nolco_used += take
                remaining -= take
                if remaining <= 0:
                    break
        taxable = flt(net_before_nolco - nolco_used, 2)
        L += [("NOLCO", "Less: Net Operating Loss Carry-Over (itemized only)", flt(nolco_used, 2), "computed"), ("Taxable income", "Net Taxable Income", taxable, "computed")]

        if option == "Corporate":
            size = "small" if c.get("ph_corp_small") else "regular"
            rule = resolve("income", end, taxpayer="corporation", size=size)
            rcit = flt(max(taxable, 0) * flt(rule.rate) / 100, 2)
            mcit = 0.0
            mcit_rule = None
            start_year = c.get("ph_operations_start_year")
            if start_year and year >= int(start_year) + 4:
                mcit_rule = resolve("income", end, taxpayer="corporation", mcit="1")
                mcit = flt(max(gross_income, 0) * flt(mcit_rule.rate) / 100, 2)
            tax_due = max(rcit, mcit)
            L += [
                ("RCIT", f"Regular corporate income tax {flt(rule.rate):g}% ({rule.rule_id})", rcit, "computed"),
                ("MCIT", f"Minimum corporate income tax {flt(mcit_rule.rate):g}% of gross income ({mcit_rule.rule_id})" if mcit_rule else "Minimum corporate income tax (not yet applicable)", mcit, "computed"),
                ("Excess MCIT", "Excess MCIT over RCIT this period (carried forward 3 years)", flt(max(mcit - rcit, 0), 2), "computed"),
            ]
        else:
            tax_due = graduated_tax(taxable)
            L += [("Rate", "Graduated table 2023 onward (IIT-GRADUATED-2023)", 0.0, "computed")]

    credits_2307 = _credits_2307(company, cumulative_start, end)
    form_q = "1701Q" if option != "Corporate" else "1702Q"
    prior = _prior_quarters_tax(company, form_q, year, start) if True else 0.0
    L += [
        ("Tax due", "Income Tax Due", flt(tax_due, 2), "computed"),
        ("Credits 2307", "Less: Creditable tax withheld per 2307 (cumulative)", credits_2307, "computed"),
        ("Prior quarters", "Less: Tax due in earlier quarters of the year", prior, "carried"),
        ("Payable", "Tax Payable/(Overpayment)", flt(tax_due - credits_2307 - prior, 2), "computed"),
    ]
    return L


def compute_1702q(company, start, end):
    return compute_income_tax(company, start, end, annual=False)


def compute_1701q(company, start, end):
    return compute_income_tax(company, start, end, annual=False)


def compute_annual(company, start, end):
    return compute_income_tax(company, start, end, annual=True)


def register():
    from ph_cas.tax import returns

    returns.COMPUTES.update({"1702Q": compute_1702q, "1701Q": compute_1701q, "1701": compute_annual, "1701A": compute_annual, "1702-RT": compute_annual})


register()
