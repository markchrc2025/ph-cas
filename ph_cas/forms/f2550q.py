"""BIR Form 2550Q, Quarterly Value-Added Tax Return (April 2024 ENCS).

Data keys, after the Portal's editor. Books (fed from the quarter's posted records):
  i31a vatable sales, i32a zero-rated, i33a exempt, i35b output VAT on uncollected
  receivables, i36b recovered, i38 carried over, i39 deferred on capital goods from
  the previous quarter, i44a/b domestic purchases and input tax, i45a/b services by
  non-residents, i46a/b importations, i48a purchases with no input tax, i49a exempt
  imports, sch2_ratable (53), i55 input VAT on unpaid payables, i58 settled addback,
  sch3 rows (VAT withheld per 2307 received: date, agent, income, tax).
Typed: i40, i41, i42 (+i42label), i47a/b (+i47label), i49a, i52, sch1 rows (capital
  goods over 1M: c0 date, c1 source, c2 description, c3 amount, c4 balance previous,
  c5 life, c6 recognized, c7 allowed, c8 balance next), sch2_direct, i54, i56
  (+i56label), i17 / sch4 rows (advance payments), i18, i19 (+i19label), i22 to i24,
  classification, taxRelief/reliefKind/taxReliefSpec, shortPeriod.
Derived (never stored): i31b, i34a/b, i37, i43, i50a/b, i51, i57, i59, i60, i61, i15,
  i16 (from sch3), i17 (from sch4), i20, i21, i25, i26, the schedule totals.
Whole pesos.
"""

from decimal import Decimal

import frappe
from frappe.utils import flt

from ph_cas.forms.engine import Context
from ph_cas.forms.export import ExportRefusal, amt, enc, file_name, rb, tin_parts
from ph_cas.forms.money import ZERO, dec, nonneg, text, whole_peso
from ph_cas.forms.needs import Need, draft_need
from ph_cas.forms.period import mdy

NS = "frm2550qv2024:"
SCHEDULE_ROWS = {"sch1": 2, "sch3": 2, "sch4": 2}
CLASSES = ("Micro", "Small", "Medium", "Large")

# The typed inputs the form view shows (key, label, type); books keys are shown from the feed.
INPUTS = [
    ("classification", "Taxpayer classification (Item 13)", "select:Micro,Small,Medium,Large"),
    ("taxRelief", "Availing of tax relief (Item 14)", "select:no,yes"),
    ("reliefKind", "Relief kind", "select:treaty,special"),
    ("taxReliefSpec", "Relief: specify (Item 14A)", "text"),
    ("shortPeriod", "Short period return", "select:no,yes"),
    ("i40", "40 Transitional input tax", "money"),
    ("i41", "41 Presumptive input tax", "money"),
    ("i42", "42 Others", "money"),
    ("i42label", "42 specify", "text"),
    ("i47a", "47A Others: purchases", "money"),
    ("i47b", "47B Others: input tax", "money"),
    ("i47label", "47 specify", "text"),
    ("i52", "52 Input tax on capital goods deferred (if no Schedule 1 rows)", "money"),
    ("sch2_direct", "53 Schedule 2: input tax directly attributable to exempt sales", "money"),
    ("i54", "54 VAT refund or TCC claimed", "money"),
    ("i56", "56 Others", "money"),
    ("i56label", "56 specify", "text"),
    ("i17", "17 Advance payments (if no Schedule 4 rows)", "money"),
    ("i18", "18 VAT paid in return previously filed (amended)", "money"),
    ("i19", "19 Other credits", "money"),
    ("i19label", "19 specify", "text"),
    ("i22", "22 Surcharge", "money"),
    ("i23", "23 Interest", "money"),
    ("i24", "24 Compromise", "money"),
]
SCHEDULES = {
    "sch1": ("Schedule 1: capital goods over 1,000,000 (2 rows on the paper)", ["Date", "Source", "Description", "Amount", "Balance prev", "Life (months)", "Recognized", "Allowed", "Balance next"]),
    "sch3": ("Schedule 3: creditable VAT withheld (2 rows)", ["Period", "Withholding agent", "Income payment", "Tax withheld"]),
    "sch4": ("Schedule 4: advance payments (2 rows)", ["Date", "Miller", "Taxpayer", "OR number", "Amount paid"]),
}


# ---- books -------------------------------------------------------------------------
def feed(ctx: Context) -> dict:
    """The quarter's figures from the tax engine's 2550Q computation (ph_cas.tax.returns),
    one books line per item, and Schedule 3 from the 2307s received for VAT."""
    from ph_cas.tax.returns import compute_2550q

    company = ctx.company["name"]
    start, end = ctx.period.start, ctx.period.end
    lines = {item: (flt(amount), label) for item, label, amount, _src in compute_2550q(company, start, end)}
    keys = {"31A": "i31a", "32A": "i32a", "33A": "i33a", "35B": "i35b", "36B": "i36b", "38B": "i38", "39B": "i39", "44A": "i44a", "44B": "i44b", "45A": "i45a", "45B": "i45b", "46A": "i46a", "46B": "i46b", "48A": "i48a", "53B": "sch2_ratable", "55B": "i55", "58B": "i58"}
    figures, out_lines, warnings = {}, [], []
    si = f"/app/sales-invoice?company={company}&docstatus=1&posting_date=%5B%22Between%22%2C%5B%22{start}%22%2C%22{end}%22%5D%5D"
    pi = si.replace("sales-invoice", "purchase-invoice")
    n_si = frappe.db.count("Sales Invoice", {"company": company, "docstatus": 1, "posting_date": ["between", [start, end]]})
    n_pi = frappe.db.count("Purchase Invoice", {"company": company, "docstatus": 1, "posting_date": ["between", [start, end]]})
    for item, key in keys.items():
        if item not in lines:
            continue
        v, label = lines[item]
        if v < 0:
            warnings.append(f"Item {item} ({label}) is below zero in the books ({v}); it is shown as 0.")
        figures[key] = text(whole_peso(nonneg(dec(v))), 0)
        sales_side = item[0] == "3"
        out_lines.append({"key": key, "label": f"Item {item}, {label}", "amount": figures[key], "records": n_si if sales_side else n_pi, "filter": si if sales_side else pi})
    # Schedule 3: the 2307s received for VAT withheld, one row per certificate
    certs = frappe.db.sql(
        """select d.name, d.customer, d.period_from, d.period_to, sum(l.base_total) as income, sum(l.tax_withheld) as tax
           from `tabPH 2307 Received` d join `tabPH 2307 Received Line` l on l.parent = d.name
           where d.docstatus = 1 and d.company = %s and l.kind = 'VAT' and d.period_from >= %s and d.period_to <= %s
           group by d.name order by d.period_from""",
        (company, start, end),
        as_dict=True,
    )
    if certs:
        rows = []
        for c in certs:
            agent = frappe.db.get_value("Customer", c.customer, "ph_registered_name") or c.customer
            rows.append({"c0": mdy(c.period_from, True), "c1": agent, "c2": text(whole_peso(dec(c.income)), 0), "c3": text(whole_peso(dec(c.tax)), 0)})
        figures["sch3"] = rows
        out_lines.append({"key": "sch3", "label": "Schedule 3, VAT withheld per 2307 received", "amount": text(sum(whole_peso(dec(c.tax)) for c in certs), 0), "records": len(certs), "filter": f"/app/ph-2307-received?company={company}&docstatus=1"})
        if len(certs) > SCHEDULE_ROWS["sch3"]:
            warnings.append(f"Schedule 3 has {len(certs)} certificates; the paper has room for {SCHEDULE_ROWS['sch3']} rows. Combine them by agent or attach a schedule.")
    if ctx.extra.get("amends"):
        prev = frappe.db.get_value("PH Tax Return Line", {"parent": ctx.extra["amends"], "item": "26"}, "amount") or 0
        figures["i18"] = text(whole_peso(nonneg(dec(prev))), 0)
        out_lines.append({"key": "i18", "label": "Item 18, VAT paid in the return previously filed", "amount": figures["i18"], "records": 1, "filter": f"/app/ph-tax-return/{ctx.extra['amends']}"})
    return {"figures": figures, "lines": out_lines, "warnings": warnings}


# ---- compute -----------------------------------------------------------------------
def _rows(data: dict, key: str) -> list[dict]:
    v = data.get(key)
    return v if isinstance(v, list) else []


def _col_total(rows: list[dict], c: int) -> Decimal:
    return sum((whole_peso(dec(r.get(f"c{c}"))) for r in rows), ZERO)


def _w(data: dict, key: str) -> Decimal:
    return whole_peso(dec(data.get(key)))


def compute(data: dict, ctx: Context) -> list[dict]:
    sch1, sch3, sch4 = _rows(data, "sch1"), _rows(data, "sch3"), _rows(data, "sch4")
    o: dict[str, Decimal] = {}
    o["i31a"] = _w(data, "i31a")
    o["i31b"] = whole_peso(o["i31a"] * Decimal("0.12"))
    o["i32a"], o["i33a"] = _w(data, "i32a"), _w(data, "i33a")
    o["i34a"] = o["i31a"] + o["i32a"] + o["i33a"]
    o["i34b"] = o["i31b"]
    o["i35b"], o["i36b"] = _w(data, "i35b"), _w(data, "i36b")
    o["i37"] = o["i34b"] - o["i35b"] + o["i36b"]
    o["i38"] = _w(data, "i38")
    sch1e = _col_total(sch1, 4)
    o["i39"] = sch1e or _w(data, "i39")
    o["i40"], o["i41"], o["i42"] = _w(data, "i40"), _w(data, "i41"), _w(data, "i42")
    o["i43"] = o["i38"] + o["i39"] + o["i40"] + o["i41"] + o["i42"]
    for k in ("i44a", "i44b", "i45a", "i45b", "i46a", "i46b", "i47a", "i47b", "i48a", "i49a"):
        o[k] = _w(data, k)
    o["i50a"] = o["i44a"] + o["i45a"] + o["i46a"] + o["i47a"] + o["i48a"] + o["i49a"]
    o["i50b"] = o["i44b"] + o["i45b"] + o["i46b"] + o["i47b"]
    o["i51"] = o["i43"] + o["i50b"]
    sch1i = _col_total(sch1, 8)
    o["i52"] = sch1i or _w(data, "i52")
    o["sch2Direct"], o["sch2Ratable"] = _w(data, "sch2_direct"), _w(data, "sch2_ratable")
    o["sch2Total"] = o["sch2Direct"] + o["sch2Ratable"]
    o["i53"] = o["sch2Total"] or _w(data, "i53")
    o["i54"], o["i55"], o["i56"] = _w(data, "i54"), _w(data, "i55"), _w(data, "i56")
    o["i57"] = o["i52"] + o["i53"] + o["i54"] + o["i55"] + o["i56"]
    o["i58"] = _w(data, "i58")
    o["i59"] = o["i57"] + o["i58"]
    o["i60"] = o["i51"] - o["i59"]
    o["i61"] = o["i37"] - o["i60"]
    o["i15"] = o["i61"]
    o["sch3C"], o["sch3D"] = _col_total(sch3, 2), _col_total(sch3, 3)
    o["i16"] = o["sch3D"] or _w(data, "i16")
    o["sch4"] = _col_total(sch4, 4)
    o["i17"] = o["sch4"] or _w(data, "i17")
    o["i18"], o["i19"] = _w(data, "i18"), _w(data, "i19")
    o["i20"] = o["i16"] + o["i17"] + o["i18"] + o["i19"]
    o["i21"] = o["i15"] - o["i20"]
    o["i22"], o["i23"], o["i24"] = _w(data, "i22"), _w(data, "i23"), _w(data, "i24")
    o["i25"] = o["i22"] + o["i23"] + o["i24"]
    o["i26"] = o["i21"] + o["i25"]
    o["sch1E"], o["sch1H"], o["sch1I"] = sch1e, _col_total(sch1, 7), sch1i

    kind = _kinds(data)
    derived = {"i31b", "i34a", "i34b", "i37", "i43", "i50a", "i50b", "i51", "i57", "i59", "i60", "i61", "i15", "i20", "i21", "i25", "i26"}
    out = []
    for k, label in LABELS:
        if k not in o:
            continue
        out.append({"item": k[1:].upper(), "label": label, "amount": o[k], "kind": "derived" if k in derived or (k == "i16" and sch3) or (k == "i17" and sch4) or (k in ("i39", "i52") and sch1) or (k == "i53" and o["sch2Total"]) else kind(k)})
    out.append({"item": "_o", "label": "", "amount": ZERO, "kind": "derived", "o": o})
    return out


LABELS = [
    ("i31a", "Vatable Sales/Receipts (Private)"), ("i31b", "Output Tax on Vatable Sales"), ("i32a", "Zero-Rated Sales/Receipts"), ("i33a", "Exempt Sales/Receipts"),
    ("i34a", "Total Sales/Receipts"), ("i34b", "Total Output Tax Due"), ("i35b", "Less: Output VAT on Uncollected Receivables"), ("i36b", "Add: Output VAT on Recovered Uncollected Receivables"),
    ("i37", "Total Adjusted Output Tax Due"), ("i38", "Input Tax Carried Over from Previous Quarter"), ("i39", "Input Tax Deferred on Capital Goods from Previous Quarter"), ("i40", "Transitional Input Tax"),
    ("i41", "Presumptive Input Tax"), ("i42", "Others"), ("i43", "Total (Sum of Items 38 to 42)"), ("i44a", "Purchases of Capital Goods and Other Domestic Purchases (A)"), ("i44b", "Input Tax on Domestic Purchases (B)"),
    ("i45a", "Services Rendered by Non-Residents (A)"), ("i45b", "Input Tax on Services by Non-Residents (B)"), ("i46a", "Importation of Goods (A)"), ("i46b", "Input Tax on Importations (B)"),
    ("i47a", "Others (A)"), ("i47b", "Others (B)"), ("i48a", "Domestic Purchases with No Input Tax"), ("i49a", "Importation of Goods Exempt from VAT"), ("i50a", "Total Current Purchases (A)"), ("i50b", "Total Current Input Tax (B)"),
    ("i51", "Total Available Input Tax"), ("i52", "Input Tax on Purchases of Capital Goods Deferred for the Succeeding Period"), ("i53", "Input Tax Attributable to VAT Exempt Sales"), ("i54", "VAT Refund/TCC Claimed"),
    ("i55", "Input VAT on Unpaid Payables"), ("i56", "Others"), ("i57", "Total Deductions from Input Tax"), ("i58", "Add: Input VAT on Settled Unpaid Payables Previously Deducted"), ("i59", "Adjusted Deductions from Input Tax"),
    ("i60", "Total Allowable Input Tax"), ("i61", "Net VAT Payable/(Excess Input Tax)"), ("i15", "Net VAT Payable/(Excess Input Tax) (from Item 61)"), ("i16", "Creditable Value-Added Tax Withheld (Schedule 3)"),
    ("i17", "Advance Payments (Schedule 4)"), ("i18", "VAT Paid in Return Previously Filed, if Amended"), ("i19", "Other Credits/Payments"), ("i20", "Total Tax Credits/Payments"), ("i21", "Tax Still Payable/(Excess Credits)"),
    ("i22", "Surcharge"), ("i23", "Interest"), ("i24", "Compromise"), ("i25", "Total Penalties"), ("i26", "TOTAL AMOUNT PAYABLE/(Excess Credits)"),
]


def _kinds(data: dict):
    books = (data.get("_source") or {}).get("books") or {}

    def kind(key: str) -> str:
        return "books" if key in books and data.get(key) == books[key] else "typed"

    return kind


def _o(comp: list[dict]) -> dict:
    return next(ln for ln in comp if ln["item"] == "_o")["o"]


# ---- needs -------------------------------------------------------------------------
def needs(data: dict, ctx: Context) -> list[Need]:
    out: list[Need] = []
    cls = data.get("classification") or ctx.company.get("ph_taxpayer_class") or ""
    if cls not in CLASSES:
        out.append(draft_need(ctx.return_name, "classification", "What is the taxpayer classification under RR 8-2024 (Micro, Small, Medium, Large)?", "Item 13 marks one box.", "choice", list(CLASSES)))
    for key, n in SCHEDULE_ROWS.items():
        rows = [r for r in _rows(data, key) if any(str(r.get(f"c{c}") or "").strip() for c in range(9))]
        if len(rows) > n:
            out.append(draft_need(ctx.return_name, key, f"{SCHEDULES[key][0].split(':')[0]} has room for {n} rows; the draft has {len(rows)}. Which rows are combined or removed?", "The form cannot carry more rows.", "text"))
    for item in ("19", "42", "47", "56"):
        amount_key = "i47b" if item == "47" else f"i{item}"
        if dec(data.get(amount_key)) != 0 and not (data.get(f"i{item}label") or "").strip():
            out.append(draft_need(ctx.return_name, f"i{item}label", f"Item {item} has an amount. What is it?", f"Item {item} asks to specify.", "text"))
    if (data.get("taxRelief") or "") == "yes":
        if (data.get("reliefKind") or "") not in ("treaty", "special"):
            out.append(draft_need(ctx.return_name, "reliefKind", "Is the relief under an international tax treaty or a special law (special rate)?", "Item 14 marks one of two boxes.", "choice", ["treaty", "special"]))
        if not (data.get("taxReliefSpec") or "").strip():
            out.append(draft_need(ctx.return_name, "taxReliefSpec", "Which treaty or special law gives the relief?", "Item 14A asks to specify.", "text"))
    return out


# ---- export ------------------------------------------------------------------------
def _full_name(c: dict) -> str:
    if (c.get("ph_taxpayer_type") or "") == "Individual":
        given = " ".join(x for x in (c.get("ph_first_name"), c.get("ph_middle_name")) if x)
        return ", ".join(x for x in (c.get("ph_last_name"), given) if x)
    return c.get("ph_registered_name") or c.get("company_name") or ""


def _cell(rows: list[dict], i: int, c: int) -> str:
    r = rows[i] if i < len(rows) else None
    v = r.get(f"c{c}") if r else None
    return "" if v is None else str(v)


def export_rows(data: dict, comp: list[dict], ctx: Context) -> tuple[list[tuple[str, str]], str]:
    c = ctx.company
    o = _o(comp)
    t = tin_parts(c.get("tax_id") or "", c.get("ph_branch_code") or "00000")
    p = ctx.period
    yyyy = str(p.year)
    qn = p.quarter_no
    for key, n in SCHEDULE_ROWS.items():
        rows = [r for r in _rows(data, key) if any(str(r.get(f"c{cc}") or "").strip() for cc in range(9))]
        if len(rows) > n:
            raise ExportRefusal(f"{SCHEDULES[key][0].split(':')[0]} has {len(rows)} rows but the form has room for {n}. Combine or remove rows, then export again.")
    rows: list[tuple[str, str]] = []
    P = lambda k, v: rows.append((NS + k, v))  # noqa: E731
    G = lambda k, v: rows.append((k, v))  # noqa: E731
    fiscal = p.fiscal
    end_month = (p.end.month if fiscal else 12) if p.kind == "quarter" else 12
    if fiscal:
        from ph_cas.forms.period import fiscal_start_month

        sm = fiscal_start_month(c.get("ph_fiscal_year_start"))
        end_month = sm - 1 if sm > 1 else 12
    cls = data.get("classification") or c.get("ph_taxpayer_class") or ""
    P("calendarNo1", rb(not fiscal))
    P("fiscalNo1", rb(fiscal))
    P("selectedMonthNo2", f"{end_month:02d}")
    P("txtYearNo2", yyyy)
    for n in range(1, 5):
        P(f"OptQuarter{n}", rb(qn == n))
    P("RtnPeriodFromNo4", mdy(p.start))
    P("RtnPeriodToNo4", mdy(p.end))
    P("amendedReturnYesNo5", rb(ctx.is_amended))
    P("amendedReturnNo5", rb(not ctx.is_amended))
    short = (data.get("shortPeriod") or "") == "yes"
    P("OptShortPrd1", rb(short))
    P("OptShortPrd2", rb(not short))
    P("txtTIN1", t["t1"])
    P("txtTIN2", t["t2"])
    P("txtTIN3", t["t3"])
    P("branchCode", t["branch3"])
    P("txtRDOCode", c.get("ph_rdo") or "")
    P("taxpayerName", enc(_full_name(c)))
    P("taxpayerAddress", enc(" ".join((c.get("ph_registered_address") or "").split())))
    P("taxpayerZip", c.get("ph_zip") or "")
    P("taxpayerContactNumber", ctx.contact_number or c.get("ph_contact_number") or "")
    P("taxpayerEmailAddress", c.get("ph_email") or "")
    for n, name in enumerate(CLASSES, start=1):
        P(f"taxPayerClassification{n}", rb(cls == name))
    relief = (data.get("taxRelief") or "") == "yes"
    P("internationalTreatyYn", rb(relief and data.get("reliefKind") == "treaty"))
    P("specialRateYn", rb(relief and data.get("reliefKind") != "treaty"))
    P("specifyInternationalTreaty", enc(data.get("taxReliefSpec")))
    P("excessInputTax", amt(0))
    P("creditableVat", amt(o["i16"]))
    P("advVatPayment", amt(o["i17"]))
    P("vatPaidReturn", amt(o["i18"]))
    P("addSpecifyNo19", enc(data.get("i19label")))
    P("otherCreditsNo19", amt(o["i19"]))
    P("totalTaxCredits", amt(o["i20"]))
    P("excessCredits", amt(o["i21"]))
    P("surcharge", amt(o["i22"]))
    P("interest", amt(o["i23"]))
    P("compromise", amt(o["i24"]))
    P("penalties", amt(o["i25"]))
    P("totalPayable", amt(o["i26"]))
    P("txtPg2TIN1", t["t1"])
    P("txtPg2TIN2", t["t2"])
    P("txtPg2TIN3", t["t3"])
    P("txtPg2BranchCode", t["branch3"])
    P("Pg2TaxPayer", _full_name(c))
    for k, key in (("vatableSales", "i31a"), ("outputVatSales", "i31b"), ("zeroRatedSales", "i32a"), ("exemptSales", "i33a"), ("totalSales", "i34a"), ("outputTaxDue", "i34b"), ("lessOutputVat", "i35b"), ("addOutputVat", "i36b"), ("totalAdjOutput", "i37"), ("inputTaxCarried", "i38"), ("inputTaxDeferred", "i39"), ("transitionalInputTax", "i40"), ("presumptiveInputTax", "i41")):
        P(k, amt(o[key]))
    P("addSpecifyNo42", enc(data.get("i42label")))
    P("otherSpecify42", amt(o["i42"]))
    P("total43", amt(o["i43"]))
    for k, key in (("domesticPurchase", "i44a"), ("domesticInputTax", "i44b"), ("servicesPurchase", "i45a"), ("serviceInputTax", "i45b"), ("importPurchase", "i46a"), ("importInputTax", "i46b")):
        P(k, amt(o[key]))
    P("addSpecifyNo47", enc(data.get("i47label")))
    P("otherSpecify47", amt(o["i47a"]))
    G("otherSpecify47B", amt(o["i47b"]))
    for k, key in (("domesticPurchaseNoTax", "i48a"), ("vatExemptImports", "i49a"), ("totalCurPurchase", "i50a"), ("totalCurInputTax", "i50b"), ("totalAvailInputTax", "i51"), ("importCapitalInputTax", "i52"), ("inputTaxAttr", "i53"), ("vatRefund", "i54"), ("inputVatUnpaid", "i55")):
        P(k, amt(o[key]))
    P("addSpecifyNo56", enc(data.get("i56label")))
    P("otherSpecify56", amt(o["i56"]))
    for k, key in (("totalDeductions", "i57"), ("addInputVat", "i58"), ("adjDeductions", "i59"), ("totalAllowInputTax", "i60"), ("netVatPayable", "i61")):
        P(k, amt(o[key]))
    sch1 = _rows(data, "sch1")
    for i, n in enumerate(("10", "11")):
        G(f"txtDatePurchase{n}", _cell(sch1, i, 0))
        G(f"txtSourceCode{n}", _cell(sch1, i, 1))
        G(f"txtDescription{n}", enc(_cell(sch1, i, 2)))
        G(f"txtAmountPurchase{n}", amt(_cell(sch1, i, 3)))
        G(f"txtInputTax{n}", amt(_cell(sch1, i, 4)))
        G(f"txtEstimatedLife{n}", amt(_cell(sch1, i, 5)))
        G(f"txtRecognizedLife{n}", amt(_cell(sch1, i, 6)))
        G(f"txtAllowedInputTax{n}", amt(_cell(sch1, i, 7)))
        G(f"txtBalanceInputTax{n}", amt(_cell(sch1, i, 8)))
    G("sched1TotalBalPrev", amt(o["sch1E"]))
    G("sched1TotalBalNext", amt(o["sch1I"]))
    P("sched2InputTaxDirect", amt(o["sch2Direct"]))
    P("sched2VatExemptSale", amt(0))
    P("sched2AmountInputTax", amt(0))
    P("sched2TotalSales", amt(0))
    P("sched2TotalRatable", amt(o["sch2Ratable"]))
    P("sched2TotalAttr", amt(o["sch2Total"]))
    sch3 = _rows(data, "sch3")
    for i, n in enumerate(("30", "31")):
        G(f"txtDateCovered{n}", _cell(sch3, i, 0))
        G(f"txtDateCovered3To{n[-1]}", "")
        G(f"txtNameWithHoldingAgent{n}", enc(_cell(sch3, i, 1)))
        G(f"txtIncomePayment{n}", amt(_cell(sch3, i, 2)))
        G(f"txtTotalTaxWithHeld{n}", amt(_cell(sch3, i, 3)))
    G("sched3TotalIncome", amt(o["sch3C"]))
    G("sched3TotalTax", amt(o["sch3D"]))
    sch4 = _rows(data, "sch4")
    for i, n in enumerate(("40", "41")):
        G(f"txtDate{n}", _cell(sch4, i, 0))
        G(f"txtDate4To{n[-1]}", "")
        G(f"txtNameOfMiller{n}", enc(_cell(sch4, i, 1)))
        G(f"txtNameOfTaxpayer{n}", enc(_cell(sch4, i, 2)))
        G(f"txtOfficialReceiptNumber{n}", enc(_cell(sch4, i, 3)) if _cell(sch4, i, 3) else amt(0))
        G(f"txtAmountPaid{n}", amt(_cell(sch4, i, 4)))
    G("sched4AmountPaid", amt(o["sch4"]))
    P("txtCurrentPage", "1")
    P("txtMaxPage", "2")
    G("resultOtherCreditsNo19", amt(o["i19"]))
    G("resultOtherCreditsNo42", amt(o["i42"]))
    G("resultOtherCreditsNo47", amt(o["i47b"]))
    G("resultOtherCreditsNo56", amt(o["i56"]))
    G("txtTotalAmountOfBalanceofInputTaxFromPrevious", amt(o["sch1E"]))
    G("txtTotalAmountOfBalanceofInputTaxToBeCarried", amt(o["sch1I"]))
    G("txtTotalAmountofIncomePayment", amt(o["sch3C"]))
    G("txtTotalAmoungOfTaxWithHeld", amt(o["sch3D"]))
    G("txtAmountPaidSched4", amt(o["sch4"]))
    G("txtFinalFlag", "1" if ctx.final else "0")
    G("txtEnroll", "Y")
    G("ebirOnlineConfirmUsername", "")
    G("ebirOnlineUsername", "")
    G("ebirOnlineSecret", "")
    G("txtEmail", "")
    G("driveSelectTPExport", "0")
    G("dateFiled", ctx.date_filed or "")
    return rows, file_name(c.get("tax_id") or "", c.get("ph_branch_code") or "00000", "2550Q", "2024", f"{end_month:02d}", yyyy, qn)


def filed_snapshot_extra(data: dict, ctx: Context) -> dict:
    return {"schedules": {k: _rows(data, k) for k in ("sch1", "sch3", "sch4")}}


def key_figures(comp: list[dict]) -> dict[str, Decimal]:
    o = _o(comp)
    return {"output_tax": o["i37"], "input_tax": o["i60"], "net": o["i61"], "payable": o["i26"]}


# ---- SLSP tie-out (LDG-81) --------------------------------------------------------
def slsp_tie_out(data: dict, ctx: Context) -> list[str]:
    """Compare the quarter's RELIEF sales and purchases totals with the return's items.
    A mismatch is a warning the user clears before filing."""
    from ph_cas.dat.relief import build_purchases, build_sales, months

    company = ctx.company["name"]
    out = []
    sales = inputs = dec("0")
    for start, end in months(ctx.period.start, ctx.period.end):  # three monthly files (RDO answer 11)
        try:
            _n, s_bytes, _k = build_sales(company, start, end)
            _n, p_bytes, _k = build_purchases(company, start, end)
        except Exception as e:  # the writer refuses (a party without an address, say): say so, do not block
            return [f"SLSP could not be built for the tie-out: {e}"]
        s_head = s_bytes.decode("utf-8", errors="replace").splitlines()[0].split(",")
        p_head = p_bytes.decode("utf-8", errors="replace").splitlines()[0].split(",")
        try:
            sales += dec(s_head[10]) + dec(s_head[11]) + dec(s_head[12])
            inputs += dec(p_head[15])  # the purchases header's input tax total
        except (IndexError, ValueError):
            return ["SLSP header could not be read for the tie-out."]
    slsp_sales, slsp_input = whole_peso(sales), whole_peso(inputs)
    o = _o(compute(data, ctx))
    if slsp_sales != o["i34a"]:
        out.append(f"SLSP sales ({slsp_sales}) differ from Item 34A ({o['i34a']}).")
    if slsp_input != o["i44b"]:
        out.append(f"SLSP input tax ({slsp_input}) differs from Item 44B ({o['i44b']}).")
    return out
