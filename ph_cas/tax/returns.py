"""B16 onward: period figures for each return, computed from the ledger and
the tax fields the engine stored on documents. Nothing here is typed; typed
adjustments live in their own table on PH Tax Return Figures.

Each compute returns [(item, label, amount, source)] in the BIR form's item
order and ends with the derived totals.
"""

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate


def _sum(table: str, field: str, filters: str, params: dict) -> float:
    row = frappe.db.sql(f"select coalesce(sum(`{field}`), 0) from `tab{table}` where {filters}", params)
    return flt(row[0][0]) if row else 0.0


def quarter_bounds(date) -> tuple:
    d = getdate(date)
    q_start_month = ((d.month - 1) // 3) * 3 + 1
    start = getdate(f"{d.year}-{q_start_month:02d}-01")
    return start, get_last_day(add_months(start, 2))


def previous_period_figure(company: str, form: str, period_start, item: str) -> float:
    """The named item of the most recent earlier computed return of the same form."""
    prev = frappe.get_all(
        "PH Tax Return Figures",
        filters={"company": company, "form": form, "period_end": ("<", period_start)},
        fields=["name"],
        order_by="period_end desc",
        limit=1,
    )
    if not prev:
        return 0.0
    doc = frappe.get_doc("PH Tax Return Figures", prev[0].name)
    return doc.figure(item)


# ---- 2550Q (April 2024 ENCS) ---------------------------------------------------


def compute_2550q(company: str, start, end) -> list:
    p = {"company": company, "start": start, "end": end}
    si = "company = %(company)s and docstatus = 1 and posting_date between %(start)s and %(end)s"
    pi = si

    vatable = _sum("Sales Invoice", "ph_vatable_sales", si, p)
    output_vat = _sum("Sales Invoice", "ph_vat_amount", si, p)
    zero = _sum("Sales Invoice", "ph_zero_rated_sales", si, p)
    exempt = _sum("Sales Invoice", "ph_exempt_sales", si, p)
    total_sales = flt(vatable + zero + exempt, 2)

    # 35 and 36: output VAT credit on uncollected receivables (RR 3-2024), by claim flags on the invoice
    claimed = _sum("Sales Invoice", "ph_vat_amount", "company = %(company)s and docstatus = 1 and ph_ovc_claimed = 1 and ph_ovc_claim_quarter = %(label)s", {"company": company, "label": _qlabel(start)})
    recovered = _recovered_output_vat(company, start, end)
    adjusted_output = flt(output_vat - claimed + recovered, 2)

    carried = previous_period_figure(company, "2550Q", start, "61")
    carried = -carried if carried < 0 else 0.0  # an excess (negative 61) carries over as input tax
    deferred_prev = previous_period_figure(company, "2550Q", start, "52")

    dom_purchases = _sum("Purchase Invoice", "ph_input_vat_goods", pi, p) / 0.12 if False else 0.0
    goods_in = _sum("Purchase Invoice", "ph_input_vat_goods", pi, p)
    services_in = _sum("Purchase Invoice", "ph_input_vat_services", pi, p)
    capital_in = _sum("Purchase Invoice", "ph_input_vat_capital", pi, p)
    # RBE input VAT is claimable only after the bill is paid; DSP input VAT at once
    rbe_in = _sum("Purchase Invoice", "ph_rc_input_vat", pi + " and ph_rc_kind = 'RBE purchase' and outstanding_amount = 0", p)
    dsp_in = _sum("Purchase Invoice", "ph_rc_input_vat", pi + " and ph_rc_kind = 'Digital services (non-resident)'", p)
    dsp_base = _sum("Purchase Invoice", "ph_rc_base", pi + " and ph_rc_kind = 'Digital services (non-resident)'", p)
    rbe_base = _sum("Purchase Invoice", "ph_rc_base", pi + " and ph_rc_kind = 'RBE purchase' and outstanding_amount = 0", p)
    domestic_in = flt(goods_in + services_in + capital_in + rbe_in, 2)
    domestic_base = flt(_vat_base(company, start, end) + rbe_base, 2)
    no_input = _sum("Purchase Invoice", "ph_exempt_purchases", pi, p)
    imports_base = _sum("Purchase Invoice", "ph_import_dutiable_value", pi + " and ph_is_import = 1", p) if frappe.get_meta("Purchase Invoice").has_field("ph_is_import") else 0.0
    imports_in = _sum("Purchase Invoice", "ph_input_vat_import", pi + " and ph_is_import = 1", p) if frappe.get_meta("Purchase Invoice").has_field("ph_input_vat_import") else 0.0

    current_in = flt(domestic_in + dsp_in + imports_in, 2)
    total_available = flt(carried + deferred_prev + current_in, 2)

    # 53: input tax attributable to exempt sales, ratable method (NIRC 110; H9)
    attributable = flt(current_in * (exempt / total_sales), 2) if total_sales and exempt else 0.0
    unpaid_reversal = _sum("Purchase Invoice", "ph_input_vat_goods", pi + " and ph_supplier_claimed_ovc = 1", p) + _sum("Purchase Invoice", "ph_input_vat_services", pi + " and ph_supplier_claimed_ovc = 1", p) if frappe.get_meta("Purchase Invoice").has_field("ph_supplier_claimed_ovc") else 0.0
    settled_addback = _settled_unpaid_payables(company, start, end)
    deductions = flt(attributable + unpaid_reversal, 2)
    adjusted_deductions = flt(deductions + settled_addback, 2)
    allowable = flt(total_available - adjusted_deductions, 2)
    net = flt(adjusted_output - allowable, 2)

    cvat_withheld = _creditable_vat_withheld(company, start, end)
    total_credits = flt(cvat_withheld, 2)
    still_payable = flt(net - total_credits, 2)

    L = []
    L.append(("31A", "VATable Sales", vatable, "computed"))
    L.append(("31B", "Output Tax on VATable Sales", output_vat, "computed"))
    L.append(("32A", "Zero-Rated Sales", zero, "computed"))
    L.append(("33A", "Exempt Sales", exempt, "computed"))
    L.append(("34A", "Total Sales", total_sales, "computed"))
    L.append(("34B", "Total Output Tax Due", output_vat, "computed"))
    L.append(("35B", "Less: Output VAT on Uncollected Receivables", claimed, "computed"))
    L.append(("36B", "Add: Output VAT on Recovered Uncollected Receivables", recovered, "computed"))
    L.append(("37B", "Total Adjusted Output Tax Due", adjusted_output, "computed"))
    L.append(("38B", "Input Tax Carried Over from Previous Quarter", carried, "carried"))
    L.append(("39B", "Input Tax Deferred on Capital Goods from Previous Quarter", deferred_prev, "carried"))
    L.append(("43B", "Total (38B to 42B)", flt(carried + deferred_prev, 2), "computed"))
    L.append(("44A", "Domestic Purchases", domestic_base, "computed"))
    L.append(("44B", "Input Tax on Domestic Purchases", domestic_in, "computed"))
    L.append(("45A", "Services Rendered by Non-Residents", dsp_base, "computed"))
    L.append(("45B", "Input Tax on Services by Non-Residents", dsp_in, "computed"))
    L.append(("46A", "Importations", imports_base, "computed"))
    L.append(("46B", "Input Tax on Importations", imports_in, "computed"))
    L.append(("48A", "Domestic Purchases with No Input Tax", no_input, "computed"))
    L.append(("50A", "Total Current Purchases", flt(domestic_base + dsp_base + imports_base + no_input, 2), "computed"))
    L.append(("50B", "Total Current Input Tax", current_in, "computed"))
    L.append(("51B", "Total Available Input Tax", total_available, "computed"))
    L.append(("52B", "Input Tax on Capital Goods Deferred for the Succeeding Period", 0.0, "computed"))
    L.append(("53B", "Input Tax Attributable to VAT Exempt Sales", attributable, "computed"))
    L.append(("55B", "Input VAT on Unpaid Payables", unpaid_reversal, "computed"))
    L.append(("57B", "Total Deductions from Input Tax", deductions, "computed"))
    L.append(("58B", "Add: Input VAT on Settled Unpaid Payables Previously Deducted", settled_addback, "computed"))
    L.append(("59B", "Adjusted Deductions from Input Tax", adjusted_deductions, "computed"))
    L.append(("60B", "Total Allowable Input Tax", allowable, "computed"))
    L.append(("61", "Net VAT Payable/(Excess Input Tax)", net, "computed"))
    L.append(("15", "Net VAT Payable/(Excess Input Tax) (from 61)", net, "computed"))
    L.append(("16", "Creditable VAT Withheld (Schedule 3)", cvat_withheld, "computed"))
    L.append(("20", "Total Tax Credits/Payments", total_credits, "computed"))
    L.append(("21", "Tax Still Payable/(Excess Credits)", still_payable, "computed"))
    L.append(("26", "TOTAL AMOUNT PAYABLE/(Excess Credits)", still_payable, "computed"))
    return L


def _qlabel(start) -> str:
    s = getdate(start)
    return f"{s.year}-Q{(s.month - 1) // 3 + 1}"


def _vat_base(company, start, end) -> float:
    """VAT-exclusive value of domestic purchases that carried ordinary input VAT."""
    rows = frappe.db.sql(
        """select coalesce(sum(ph_input_vat_goods + ph_input_vat_services + ph_input_vat_capital), 0)
           from `tabPurchase Invoice` where company = %s and docstatus = 1 and posting_date between %s and %s""",
        (company, start, end),
    )
    vat = flt(rows[0][0]) if rows else 0.0
    from ph_cas.tax.rules import resolve

    rate = flt(resolve("vat", end, side="purchase").rate) or 12
    return flt(vat * 100 / rate, 2)


def _recovered_output_vat(company, start, end) -> float:
    """Collections in the period on invoices whose output VAT was claimed earlier."""
    rows = frappe.db.sql(
        """select coalesce(sum(r.allocated_amount * si.ph_vat_amount / nullif(si.grand_total, 0)), 0)
           from `tabPayment Entry Reference` r
           join `tabPayment Entry` p on p.name = r.parent and p.docstatus = 1
           join `tabSales Invoice` si on si.name = r.reference_name
           where r.reference_doctype = 'Sales Invoice' and si.company = %s and si.ph_ovc_claimed = 1
             and p.posting_date between %s and %s and si.ph_ovc_claim_quarter < %s""",
        (company, start, end, _qlabel(start)),
    )
    return flt(rows[0][0], 2) if rows else 0.0


def _settled_unpaid_payables(company, start, end) -> float:
    if not frappe.get_meta("Purchase Invoice").has_field("ph_supplier_claimed_ovc"):
        return 0.0
    rows = frappe.db.sql(
        """select coalesce(sum(r.allocated_amount * (pi.ph_input_vat_goods + pi.ph_input_vat_services) / nullif(pi.grand_total, 0)), 0)
           from `tabPayment Entry Reference` r
           join `tabPayment Entry` p on p.name = r.parent and p.docstatus = 1
           join `tabPurchase Invoice` pi on pi.name = r.reference_name
           where r.reference_doctype = 'Purchase Invoice' and pi.company = %s and pi.ph_supplier_claimed_ovc = 1
             and p.posting_date between %s and %s and pi.posting_date < %s""",
        (company, start, end, start),
    )
    return flt(rows[0][0], 2) if rows else 0.0


def _creditable_vat_withheld(company, start, end) -> float:
    rows = frappe.db.sql(
        """select coalesce(sum(l.tax_withheld), 0) from `tabPH 2307 Received Line` l
           join `tabPH 2307 Received` d on d.name = l.parent
           where d.docstatus = 1 and d.company = %s and l.kind = 'VAT' and d.period_from >= %s and d.period_to <= %s""",
        (company, start, end),
    )
    return flt(rows[0][0], 2) if rows else 0.0


COMPUTES = {"2550Q": compute_2550q}


def get_or_create(company: str, form: str, start, end, compute: bool = True):
    from ph_cas.ph_cas.doctype.ph_tax_return_figures.ph_tax_return_figures import period_label

    label = period_label(form, start, end)
    abbr = frappe.get_cached_value("Company", company, "abbr")
    name = f"{form}-{label}-{abbr}"
    if frappe.db.exists("PH Tax Return Figures", name):
        doc = frappe.get_doc("PH Tax Return Figures", name)
    else:
        doc = frappe.get_doc({"doctype": "PH Tax Return Figures", "company": company, "form": form, "period_start": start, "period_end": end})
        doc.insert(ignore_permissions=True)
    if compute and not doc.filed:
        doc.compute()
        doc.save(ignore_permissions=True)
    return doc


@frappe.whitelist()
def compute_return(company: str, form: str, period_start: str, period_end: str):
    doc = get_or_create(company, form, period_start, period_end)
    return doc.name
