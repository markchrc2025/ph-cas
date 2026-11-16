"""BIR Form 1702-RT, Annual Income Tax Return for Corporations, Partnerships and
Other Non-Individual Taxpayers Subject Only to Regular Income Tax Rate
(January 2018 ENCS). Exported for eBIRForms and printed on the blank. Whole pesos.

Books (the year from the tax engine): i27 sales, i30 cost of sales, i34
ordinary allowable itemized deductions (when Schedule 1 has no rows), i36
NOLCO, i46 income tax payments under the regular rate for the first three
quarters, i48 creditable tax withheld for the first three quarters, i49
creditable tax withheld for the fourth quarter, rate and method from the
Company, mcit yes or no from the year of operations start.
Typed: i28 returns, i32 other taxable income, Schedule 1 (s1_1 to s1_17i with
descriptions), Schedule 2 (special deductions), Schedule 3A NOLCO rows
(nolco4 to nolco7: year, A to D), Schedule 4 MCIT rows (mcit1 to mcit3), i44,
i45, i50 to i54, i17 to i19, Schedule 5 (schV1 to schV8), over, signatories,
payments. Derived: the rest.
"""

from decimal import Decimal

from ph_cas.forms import income as inc
from ph_cas.forms.engine import Context
from ph_cas.forms.money import ZERO
from ph_cas.forms.needs import Need, draft_need

NS = "frm1702RT:"
S1 = [
    ("1", "Amortizations"), ("2", "Bad debts"), ("3", "Charitable contributions"), ("4", "Depletion"), ("5", "Depreciation"), ("6", "Entertainment, amusement and recreation"), ("7", "Fringe benefits"), ("8", "Interest"),
    ("9", "Losses"), ("10", "Pension trusts"), ("11", "Rental"), ("12", "Research and development"), ("13", "Salaries, wages and allowances"), ("14", "SSS, GSIS, Philhealth, HDMF and other contributions"), ("15", "Taxes and licenses"), ("16", "Transportation and travel"),
    ("17a", "Janitorial and messengerial services"), ("17b", "Professional fees"), ("17c", "Security services"), ("17d", "Others (specify)"), ("17e", "Others (specify)"), ("17f", "Others (specify)"), ("17g", "Others (specify)"), ("17h", "Others (specify)"), ("17i", "Others (specify)"),
]
INPUTS = (
    [
        ("atcChoice", "5 ATC chosen (blank: the higher of MCIT and the regular tax)", "select:mcit,regular"),
        ("regularAtc", "5 Other ATC at the regular rate (blank: IC010, corporation in general)", "select:IC010,IC020,IC040,IC041,IC070"),
        ("rate", "Income tax rate % (25, or 20 for small corporations)", "text"),
        ("method", "13 Method of deduction", "select:itemized,osd"),
        ("mcit", "Minimum corporate income tax applies (4th year onward)", "select:yes,no"),
        ("over", "21 Overpayment: refund, TCC or carry over", "select:refund,tcc,carry"),
        ("attachments", "Number of attachments", "text"),
        ("shortPeriod", "4 Short period return", "select:no,yes"),
        ("presTitle", "Signatory 1 (president): title", "text"),
        ("presTin", "Signatory 1 (president): TIN", "text"),
        ("treasurer", "Signatory 2 (treasurer): name", "text"),
        ("treasTitle", "Signatory 2 (treasurer): title", "text"),
        ("treasTin", "Signatory 2 (treasurer): TIN", "text"),
        ("i27", "27 Sales/revenues/receipts/fees", "money"),
        ("i28", "28 Less: sales returns, allowances and discounts", "money"),
        ("i30", "30 Less: cost of sales or services", "money"),
        ("i32", "32 Add: other taxable income not subjected to final tax", "money"),
        ("i34", "34 Ordinary allowable itemized deductions (if Schedule 1 is blank)", "money"),
        ("i35", "35 Special allowable itemized deductions (if Schedule 2 is blank)", "money"),
        ("i36", "36 NOLCO (if Schedule 3A is blank)", "money"),
        ("i44", "44 Prior year's excess credits other than MCIT", "money"),
        ("i45", "45 Income tax payment under MCIT from previous quarters", "money"),
        ("i46", "46 Income tax payment under regular rate from previous quarters", "money"),
        ("i47", "47 Excess MCIT applied this year (if Schedule 4 is blank)", "money"),
        ("i48", "48 Creditable tax withheld from previous quarters", "money"),
        ("i49", "49 Creditable tax withheld per 2307 for the fourth quarter", "money"),
        ("i50", "50 Foreign tax credits", "money"),
        ("i51", "51 Tax paid in return previously filed (amended)", "money"),
        ("i52", "52 Special tax credits", "money"),
        ("i53", "53 Other credits (specify)", "money"),
        ("i53desc", "53 specify", "text"),
        ("i54", "54 Other credits (specify)", "money"),
        ("i54desc", "54 specify", "text"),
        ("i17", "17 Surcharge", "money"),
        ("i18", "18 Interest", "money"),
        ("i19", "19 Compromise", "money"),
    ]
    + [(f"s1_{k}", f"Sch 1.{k} {label}", "money") for k, label in S1]
    + [(f"s1_17{k}desc", f"Sch 1.17{k} specify", "text") for k in "defghi"]
    + [(f"s2_{n}{suffix}", f"Sch 2.{n} {what}", kind) for n in (1, 2, 3, 4) for suffix, what, kind in (("desc", "description", "text"), ("legal", "legal basis", "text"), ("amt", "amount", "money"))]
    + [(f"nolco{n}{col}", f"Sch 3A row {n}: {what}", kind) for n in (4, 5, 6, 7) for col, what, kind in (("Year", "year incurred", "text"), ("A", "amount", "money"), ("B", "applied previous year", "money"), ("C", "applied previous year", "money"), ("D", "applied current year", "money"))]
    + [(f"mcit{n}{col}", f"Sch 4 row {n}: {what}", kind) for n in (1, 2, 3) for col, what, kind in (("Year", "year", "text"), ("A", "normal income tax", "money"), ("B", "MCIT", "money"), ("C", "excess MCIT", "money"), ("D", "applied previous year", "money"), ("E", "expired", "money"), ("F", "applied current year", "money"))]
    + [(f"schV{n}", f"Sch 5 Item {n}", "money") for n in (1, 2, 3, 5, 6, 7, 8)]
    + [(f"schV{n}desc", f"Sch 5 Item {n} specify", "text") for n in (2, 3, 5, 6, 7, 8)]
    + [(f"pay{n}{k}", f"{n} {what}: {col}", kind) for n, what in ((23, "Cash/bank debit memo"), (24, "Check"), (26, "Others")) for k, col, kind in (("bank", "bank", "text"), ("num", "number", "text"), ("date", "date (MM/DD/YYYY)", "text"), ("amt", "amount", "money"))]
    + [("pay25num", "25 Tax debit memo: number", "text"), ("pay25date", "25 date (MM/DD/YYYY)", "text"), ("pay25amt", "25 amount", "money")]
)
NOLCO_ROWS, MCIT_ROWS = (4, 5, 6, 7), (1, 2, 3)


def feed(ctx: Context) -> dict:
    company = ctx.company["name"]
    c = ctx.company
    p = ctx.period
    from ph_cas.forms.period import fiscal_start_month, quarter_range

    a = inc.annual(company, p.start, p.end)
    sm = fiscal_start_month(c.get("ph_fiscal_year_start")) if p.fiscal else 1
    q3_end = quarter_range(p.year, 3, sm)[1]
    through_q3 = inc._engine(company, p.start, q3_end, annual=False)
    osd = (c.get("ph_deduction_method") or "Itemized") != "Itemized"
    start_year = c.get("ph_operations_start_year")
    credits = a.get("Credits 2307", ZERO)
    credits_q3 = through_q3.get("Credits 2307", ZERO)
    paid_regular, paid_mcit, missing = inc.quarter_payments(company, "1702Q", p.year, (1, 2, 3), c.get("ph_fiscal_year_start") if p.fiscal else None)
    figures = {
        "rate": "20" if c.get("ph_corp_small") else "25",
        "method": "osd" if osd else "itemized",
        "mcit": "yes" if start_year and p.year >= int(start_year) + 4 else "no",
        "i27": inc.peso_text(inc.nonneg_peso(a.get("Sales"))),
        "i30": inc.peso_text(inc.nonneg_peso(a.get("COGS"))),
        "i45": inc.peso_text(paid_mcit),
        "i46": inc.peso_text(paid_regular),
        "i48": inc.peso_text(credits_q3),
        "i49": inc.peso_text(credits - credits_q3),
    }
    if not osd:
        figures["i34"] = inc.peso_text(inc.nonneg_peso(a.get("Deductions")))
        figures["i36"] = inc.peso_text(inc.nonneg_peso(a.get("NOLCO")))
    if ctx.extra.get("amends"):
        import frappe

        paid = frappe.db.get_value("PH Tax Return Line", {"parent": ctx.extra["amends"], "item": "21"}, "amount") or 0
        figures["i51"] = inc.peso_text(inc.nonneg_peso(paid))
    lines = [
        inc.books_line("i27", "Item 27, sales/revenues/receipts/fees for the year", figures["i27"], company, p.start, p.end),
        inc.books_line("i30", "Item 30, cost of sales or services", figures["i30"], company, p.start, p.end, "purchase-invoice"),
        {"key": "i45", "label": "Item 45, MCIT paid in the first three quarters (filed 1702Q returns)", "amount": figures["i45"], "records": 3 - len(missing), "filter": f"/app/ph-tax-return?company={company}&form=1702Q&docstatus=1"},
        {"key": "i46", "label": "Item 46, income tax paid at the regular rate in the first three quarters (filed 1702Q returns)", "amount": figures["i46"], "records": 3 - len(missing), "filter": f"/app/ph-tax-return?company={company}&form=1702Q&docstatus=1"},
        inc.books_line("i49", "Item 49, creditable tax withheld per 2307 for the fourth quarter", figures["i49"], company, p.start, p.end, "ph-2307-received"),
    ]
    if "i34" in figures:
        lines.append(inc.books_line("i34", "Item 34, ordinary allowable itemized deductions", figures["i34"], company, p.start, p.end, "purchase-invoice"))
    warnings = [f"Item {i} is below zero in the books; it is shown as 0." for i, v in (("27", a.get("Sales", ZERO)), ("30", a.get("COGS", ZERO))) if v < 0]
    warnings += inc.missing_quarters_warning("1702Q", p.year, missing, "Items 45 and 46")
    return {"figures": figures, "lines": lines, "warnings": warnings}


def _compute(data: dict, ctx: Context | None = None) -> dict:
    w = lambda k: inc.w(data, k)  # noqa: E731
    o: dict = {}
    rate = inc.dec(data.get("rate")) if inc.s(data.get("rate")) else Decimal(25)
    o["rate"] = rate
    o["i27"], o["i28"] = w("i27"), w("i28")
    o["i29"] = o["i27"] - o["i28"]
    o["i30"] = w("i30")
    o["i31"] = o["i29"] - o["i30"]
    o["i32"] = w("i32")
    o["i33"] = o["i31"] + o["i32"]
    o["method"] = inc.s(data.get("method")) or "itemized"
    o["sch1Total"] = sum((w(f"s1_{k}") for k, _l in S1), ZERO)
    o["sch2Total"] = sum((w(f"s2_{n}amt") for n in (1, 2, 3, 4)), ZERO)
    o["sch3aTotal"] = sum((w(f"nolco{n}D") for n in NOLCO_ROWS), ZERO)
    o["sch4Total"] = sum((w(f"mcit{n}F") for n in MCIT_ROWS), ZERO)
    o["i34"] = o["sch1Total"] if o["sch1Total"] > 0 else w("i34")
    o["i35"] = o["sch2Total"] if o["sch2Total"] > 0 else w("i35")
    o["i36"] = o["sch3aTotal"] if o["sch3aTotal"] > 0 else w("i36")
    o["i37"] = o["i34"] + o["i35"] + o["i36"]
    # eBIRForms: Item 38 only under OSD, else 0
    o["i38"] = inc.whole_peso(o["i33"] * Decimal("0.4")) if o["method"] == "osd" else ZERO
    o["i39"] = o["i33"] - (o["i38"] if o["method"] == "osd" else o["i37"])
    o["i40"] = rate
    o["i41"] = inc.whole_peso(o["i39"] * rate / 100)
    mcit_on = (inc.s(data.get("mcit")) or "yes") == "yes"
    end = ctx.period.end if ctx else None
    create = end is not None and (2020, 7) <= (end.year, end.month) <= (2023, 6)
    o["i42"] = inc.whole_peso(o["i33"] * (Decimal("0.01") if create else Decimal("0.02"))) if mcit_on else ZERO
    # Item 5 takes one ATC: by default the higher tax (IC055 when MCIT is higher); the
    # taxpayer may still choose the regular rate, and the tax due follows the choice.
    # Both computations (Items 41 and 42) stay on the return.
    from ph_cas.forms.f1702q import atc_choice

    o["atcChoice"] = atc_choice(data, mcit_on, o["i42"], o["i41"])
    o["mcitApplies"] = o["atcChoice"] == "mcit"
    o["i43"] = o["i42"] if o["mcitApplies"] else o["i41"]
    # Schedule 3 (net operating loss) the eBIRForms way: filled only when the ordinary
    # deductions exceed the gross income, else all zero
    loss = o["i34"] > o["i33"]
    o["sch3Gross"] = o["i33"] if loss else ZERO
    o["sch3Deductions"] = o["i34"] if loss else ZERO
    o["sch3NetLoss"] = o["i33"] - o["i34"] if loss else ZERO
    for k in ("i44", "i45", "i46", "i48", "i49", "i50", "i51", "i52", "i53", "i54"):
        o[k] = w(k)
    o["i47"] = o["sch4Total"] if o["sch4Total"] > 0 else w("i47")
    o["i55"] = sum((o[f"i{n}"] for n in range(44, 55)), ZERO)
    o["i56"] = o["i43"] - o["i55"]
    o["i14"], o["i15"], o["i16"] = o["i43"], o["i55"], o["i56"]
    o["i17"], o["i18"], o["i19"] = w("i17"), w("i18"), w("i19")
    o["i20"] = o["i17"] + o["i18"] + o["i19"]
    # eBIRForms: an overpayment (16 below zero) does not absorb penalties; 21 is then 20 alone
    o["i21"] = o["i20"] if o["i16"] < 0 and o["i20"] > 0 else o["i16"] + o["i20"]
    o["i57"] = inc.whole_peso(o["i35"] * rate / 100)
    o["i58"] = o["i52"]
    o["i59"] = o["i57"] + o["i58"]
    o["schV4"] = w("schV1") + w("schV2") + w("schV3")
    o["schV9"] = w("schV5") + w("schV6") + w("schV7") + w("schV8")
    o["schV10"] = o["schV4"] - o["schV9"]
    return o


LABELS = [
    ("i27", "27", "Sales/Revenues/Receipts/Fees"), ("i28", "28", "Less: Sales Returns, Allowances and Discounts"), ("i29", "29", "Net Sales/Revenues/Receipts/Fees"), ("i30", "30", "Less: Cost of Sales/Services"),
    ("i31", "31", "Gross Income from Operation"), ("i32", "32", "Add: Other Taxable Income Not Subjected to Final Tax"), ("i33", "33", "Total Gross Income"), ("i34", "34", "Ordinary Allowable Itemized Deductions"),
    ("i35", "35", "Special Allowable Itemized Deductions"), ("i36", "36", "NOLCO"), ("i37", "37", "Total Itemized Deductions"), ("i38", "38", "Optional Standard Deduction (40% of Item 33)"), ("i39", "39", "Net Taxable Income"),
    ("i41", "41", "Income Tax Due other than MCIT"), ("i42", "42", "Minimum Corporate Income Tax (2% of Item 33)"), ("i43", "43", "Total Income Tax Due"), ("i44", "44", "Prior Year's Excess Credits Other Than MCIT"),
    ("i45", "45", "Income Tax Payment under MCIT from Previous Quarters"), ("i46", "46", "Income Tax Payment under Regular Rate from Previous Quarters"), ("i47", "47", "Excess MCIT Applied this Current Taxable Year"), ("i48", "48", "Creditable Tax Withheld from Previous Quarters"),
    ("i49", "49", "Creditable Tax Withheld per BIR Form 2307 for the Fourth Quarter"), ("i50", "50", "Foreign Tax Credits"), ("i51", "51", "Tax Paid in Return Previously Filed, if Amended"), ("i52", "52", "Special Tax Credits"),
    ("i53", "53", "Other Credits/Payments"), ("i54", "54", "Other Credits/Payments"), ("i55", "55", "Total Tax Credits/Payments"), ("i56", "56", "Net Tax Payable/(Overpayment)"),
    ("i14", "14", "Total Income Tax Due"), ("i15", "15", "Less: Total Tax Credits/Payments"), ("i16", "16", "Net Tax Payable/(Overpayment)"), ("i17", "17", "Surcharge"), ("i18", "18", "Interest"), ("i19", "19", "Compromise"),
    ("i20", "20", "Total Penalties"), ("i21", "21", "TOTAL AMOUNT PAYABLE/(Overpayment)"), ("i57", "57", "Special Allowable Itemized Deductions x Rate"), ("i58", "58", "Add: Special Tax Credits"), ("i59", "59", "Total Tax Relief Availment"),
]
TYPED = {"i27", "i28", "i30", "i32", "i44", "i45", "i46", "i48", "i49", "i50", "i51", "i52", "i53", "i54", "i17", "i18", "i19"}


def compute(data: dict, ctx: Context) -> list[dict]:
    kind = inc.kinds(data)
    o = _compute(data, ctx)
    out = []
    for key, item, label in LABELS:
        if key in TYPED:
            k = kind(key)
        elif key == "i34" and o["sch1Total"] <= 0 or key == "i35" and o["sch2Total"] <= 0 or key == "i36" and o["sch3aTotal"] <= 0 or key == "i47" and o["sch4Total"] <= 0:
            k = kind(key)
        else:
            k = "derived"
        out.append(inc.line(item, label, o[key], k))
    out.append(inc.hidden("_c", o))
    return out


def needs(data: dict, ctx: Context) -> list[Need]:
    o = inc.payload(compute(data, ctx))
    out = inc.common_needs(data, ctx, "1702-RT", o["i16"] < 0)
    if not inc.s(data.get("presTitle")):
        out.append(draft_need(ctx.return_name, "presTitle", "Who signs as president or authorized representative (title and TIN)?", "The signature block prints the title and TIN.", "text"))
    if not inc.s(data.get("treasurer")):
        out.append(draft_need(ctx.return_name, "treasurer", "Who signs as treasurer or assistant treasurer (name, title, TIN)?", "The signature block prints the second signatory.", "text"))
    return out


def _n(d) -> str:
    v = inc.whole_peso(inc.dec(d))
    return "0" if v == 0 else inc.amt(v)


def _pad3(v) -> str:
    n = int(inc.dec(v))
    return str(max(0, n)).rjust(3, "0")[-3:]


def export_rows(data: dict, comp: list[dict], ctx: Context) -> tuple[list[tuple[str, str]], str]:
    c = ctx.company
    o = inc.payload(comp)
    t = inc.tin(c)
    p = ctx.period
    mm = f"{p.end.month:02d}"
    yy = str(p.year)[-2:]
    inc.chosen_atc(data.get("atc"), "1702-RT")  # refuses an ATC the form does not print
    itemized = o["method"] != "osd"
    name = inc.name_reg(c)
    rdo = c.get("ph_rdo") or ""
    r = inc.Rows(NS)
    sv = lambda k, v: r.p(k, inc.s(v))  # noqa: E731
    r.b("rdoPg1I1Calendar", not p.fiscal)
    r.b("rdoPg1I1Fiscal", p.fiscal)
    r.p("ddlPg1I2Month", mm)
    r.p("txtPg1I2Year", yy)
    r.b("rdoPg1I3AmmendYes", ctx.is_amended)
    r.b("rdoPg1I3AmmendNo", not ctx.is_amended)
    short = inc.s(data.get("shortPeriod")) == "yes"
    r.b("rdoPg1I4ShortPeriodYes", short)
    r.b("rdoPg1I4ShortPeriodNo", not short)
    is_mcit = o["mcitApplies"]
    regular = "".join(inc.s(data.get("regularAtc")).split()).upper() or "IC010"
    r.b("rdoPg1I5Atc", is_mcit)
    r.p("drpPg1I5AtcOther", "" if is_mcit else regular)
    r.b("rdoPg1I5AtcOther", not is_mcit)
    r.p("txtPg1Pt1I6TIN1", t["t1"])
    r.p("txtPg1Pt1I6TIN2", t["t2"])
    r.p("txtPg1Pt1I6TIN3", t["t3"])
    r.p("txtPg1Pt1I6TIN4", t["branch3"])
    r.g("BranchMaskP1", "00000")
    r.p("txtRDO", rdo)
    r.p("drpPg1Pt1I7RDOCode", rdo)
    r.enc("txtPg1Pt1I8Name1", name)
    r.e("txtPg1Pt1I8Name2")
    r.e("txtPg1Pt1I8Name3")
    r.enc("txtPg1Pt1I9Address1", inc.address(c))
    r.e("txtPg1Pt1I9Address2")
    r.e("txtPg1Pt1I9Address3")
    r.p("txtZIP", c.get("ph_zip") or "")
    r.p("txtPg1Pt1I10", inc.slash_date(c.get("ph_incorporation_date")))
    r.p("txtPg1Pt1I11Contact", ctx.contact_number or c.get("ph_contact_number") or "")
    r.p("txtPg1Pt1I12Email", c.get("ph_email") or "")
    r.b("rdoPg1Pt1I13ItemizedDeduction", itemized)
    r.b("rdoPg1Pt1I13OptionalStandard", not itemized)
    for k, key in (("txtPg1Pt2I14IncomeTax", "i14"), ("txtPg1Pt2I15TotalTaxCredits", "i15"), ("txtPg1Pt2I16NetTax", "i16"), ("txtPg1Pt2I17Surcharge", "i17"), ("txtPg1Pt2I18Interest", "i18"), ("txtPg1Pt2I19Compromise", "i19"), ("txtPg1Pt2I20TotalPenalties", "i20"), ("txtPg1Pt2I21TotalAmount", "i21")):
        r.p(k, _n(o[key]))
    over = inc.s(data.get("over")) if o["i16"] < 0 else ""  # eBIRForms opens the boxes only on an overpayment (Item 16)
    r.b("rdoPg1Pt2I21OverpaymentRefunded", over == "refund")
    r.b("rdoPg1Pt2I21OverpaymentIssued", over == "tcc")
    r.b("rdoPg1Pt2I21OverpaymentCarried", over == "carry")
    sv("txtSignaturePresident", name)
    sv("txtSignatureTreasurer", data.get("treasurer"))
    r.p("txtPg1Pt2PagesFilled", _pad3(data.get("attachments")))
    sv("txtPg1Pt2Signatory1", data.get("presTitle"))
    sv("txtPg1Pt2SignatoryTin1", data.get("presTin"))
    sv("txtPg1Pt2Signatory2", data.get("treasTitle"))
    sv("txtPg1Pt2SignatoryTin2", data.get("treasTin"))
    sv("txtPg1Pt3I23DebitMemoC1", data.get("pay23bank"))
    sv("txtPg1Pt3I23DebitMemoC2", data.get("pay23num"))
    sv("txtPg1Pt3I23DebitMemoC3Date", data.get("pay23date"))
    r.p("txtPg1Pt3I23DebitMemoC4Amount", _n(data.get("pay23amt")))
    sv("txtPg1Pt3I24CheckC1", data.get("pay24bank"))
    sv("txtPg1Pt3I24CheckC2", data.get("pay24num"))
    sv("txtPg1Pt3I24CheckC3Date", data.get("pay24date"))
    r.p("txtPg1Pt3I24CheckC4Amount", _n(data.get("pay24amt")))
    sv("txtPg1Pt3I25TaxDebitC2", data.get("pay25num"))
    sv("txtPg1Pt3I25TaxDebitDate", data.get("pay25date"))
    r.p("txtPg1Pt3I25TaxDebitC4Amount", _n(data.get("pay25amt")))
    r.e("txtPg1Pt3I26Others")
    sv("txtPg1Pt3I26OthersC1", data.get("pay26bank"))
    sv("txtPg1Pt3I26OthersC2", data.get("pay26num"))
    sv("txtPg1Pt3I26OthersC3Date", data.get("pay26date"))
    r.p("txtPg1Pt3I26OthersC4Amount", _n(data.get("pay26amt")))
    r.p("txtPg2TIN1", t["t1"])
    r.p("txtPg2TIN2", t["t2"])
    r.p("txtPg2TIN3", t["t3"])
    r.p("txtPg2TIN4", t["branch3"])
    r.g("txtBranchMaskP2", "00000")
    r.p("txtPg2RegisteredName", name)
    page2 = [
        ("txtPg2Pt4I27Sales", "i27"), ("txtPg2Pt4I28LessSales", "i28"), ("txtPg2Pt4I29NetSales", "i29"), ("txtPg2Pt4I30LessCost", "i30"), ("txtPg2Pt4I31GrossIncome", "i31"), ("txtPg2Pt4I32AddOtherTaxable", "i32"),
        ("txtPg2Pt4I33TotalGross", "i33"), ("txtPg2Pt4I34OrdinaryAllowable", "i34"), ("txtPg2Pt4I35SpecialAllowable", "i35"), ("txtPg2Pt4I36Nolco", "i36"), ("txtPg2Pt4I37TotalItemized", "i37"), ("txtPg2Pt4I38OptionalStandard", "i38"), ("txtPg2Pt4I39NetTaxable", "i39"),
    ]
    for k, key in page2:
        r.p(k, _n(o[key]))
    rate = o["rate"]
    r.p("Pg2Pt4I40IncomeTaxRate", (str(int(rate)) if rate == int(rate) else str(rate)) + "%")
    for k, key in (("txtPg2Pt4I41IncomeTaxDue", "i41"), ("txtPg2Pt4I42MinimumCorporate", "i42"), ("txtPg2Pt4I43TotalIncomeTax", "i43"), ("txtPg2Pt4I44ExcessCredits", "i44"), ("txtPg2Pt4I45IncomeTaxPaymentUnderMCIT", "i45"), ("txtPg2Pt4I46IncomeTaxUnderRegular", "i46"), ("txtPg2Pt4I47ExcessMCIT", "i47"), ("txtPg2Pt4I48CreditableTaxWithheldFromPrevious", "i48"), ("txtPg2Pt4I49CreditableTaxWithheldFor4thQuarter", "i49"), ("txtPg2Pt4I50ForeignTaxCredits", "i50"), ("txtPg2Pt4I51TaxPaidInReturn", "i51"), ("txtPg2Pt452SpecialTaxCredits", "i52")):
        r.p(k, _n(o[key]))
    sv("txtPg2Pt4I53C1", data.get("i53desc"))
    r.p("txtPg2Pt4I53C2", _n(o["i53"]))
    sv("txtPg2Pt4I54C1", data.get("i54desc"))
    r.p("txtPg2Pt4I54C2", _n(o["i54"]))
    for k, key in (("txtPg2Pt4I55TotalTaxCredits", "i55"), ("txtPg2Pt4I56NetTax", "i56"), ("txtPg2Pt5I57SpecialAllowable", "i57"), ("txtPg2Pt5I58AddSpecialTax", "i58"), ("txtPg2Pt5I59TotalTax", "i59")):
        r.p(k, _n(o[key]))
    r.p("txtPg3TIN1", t["t1"])
    r.p("txtPg3TIN2", t["t2"])
    r.p("txtPg3TIN3", t["t3"])
    r.p("txtPg3TIN4", t["branch3"])
    r.g("txtBranchMaskP3", "00000")
    r.p("txtPg3RegisteredName", name)
    s1keys = ["txtPg3Sc1I1Amortization", "txtPg3Sc1I2BadDebts", "txtPg3Sc1I3CharitableContributions", "txtPg3Sc1I4Depletion", "txtPg3Sc1I5Depreciation", "txtPg3Sc1I6Entertainment", "txtPg3Sc1I7FringeBenefits", "txtPg3Sc1I8Interest", "txtPg3Sc1I9Losses", "txtPg3Sc1I10PensionTrust", "txtPg3Sc1I11Rental", "txtPg3Sc1I12Research", "txtPg3Sc1I13Salaries", "txtPg3Sc1I14Contributions", "txtPg3Sc1I15TaxesandLicenses", "txtPg3Sc1I16TransportationandTravel", "txtPg3Sc1I17aJanitorial", "txtPg3Sc1I17bProfessionalFees", "txtPg3Sc1I17cSecurityServices"]
    for k, (field, _l) in zip(s1keys, S1):
        r.p(k, _n(data.get(f"s1_{field}")))
    for x in "defghi":
        sv(f"txtPg3Sc1I17{x}C1", data.get(f"s1_17{x}desc"))
        r.p(f"txtPg3Sc1I17{x}C2", _n(data.get(f"s1_17{x}")))
    r.p("txtPg3Sc1I18TotalOrdinaryAllowable", _n(o["sch1Total"]))
    for i in (1, 2, 3, 4):
        sv(f"txtPg3Sc2I{i}C1", data.get(f"s2_{i}desc"))
        sv(f"txtPg3Sc2I{i}C2", data.get(f"s2_{i}legal"))
        r.p(f"txtPg3Sc2I{i}C3", _n(data.get(f"s2_{i}amt")))
    r.p("txtPg3Sc2I5TotalSpecialAllowable", _n(o["sch2Total"]))
    r.p("txtPg4TIN1", t["t1"])
    r.p("txtPg4TIN2", t["t2"])
    r.p("txtPg4TIN3", t["t3"])
    r.p("txtPg4TIN4", t["branch3"])
    r.g("txtBranchMaskP4", "00000")
    r.p("txtPg4RegisteredName", name)
    r.p("txtPg4Sc3I1GrossIncome", _n(o["sch3Gross"]))
    r.p("txtPg4Sc3I2TotalDeductions", _n(o["sch3Deductions"]))
    r.p("txtPg4Sc3I3NetOperatingLoss", _n(o["sch3NetLoss"]))
    nv = lambda k: inc.whole_peso(inc.dec(data.get(k)))  # noqa: E731
    for i in NOLCO_ROWS:
        sv(f"txtPg4Sc3AI{i}C1", data.get(f"nolco{i}Year"))
        r.p(f"txtPg4Sc3AI{i}C2", _n(data.get(f"nolco{i}A")))
        r.p(f"txtPg4Sc3AI{i}C3", _n(data.get(f"nolco{i}B")))
    for i in NOLCO_ROWS:
        r.p(f"txtPg4Sc3AI{i}C4", _n(data.get(f"nolco{i}C")))
        r.p(f"txtPg4Sc3AI{i}C5", _n(data.get(f"nolco{i}D")))
        r.p(f"txtPg4Sc3AI{i}C6", _n(nv(f"nolco{i}A") - (nv(f"nolco{i}B") + nv(f"nolco{i}C") + nv(f"nolco{i}D"))))
    r.p("txtPg4Sc4I8TotalNOLCO", _n(o["sch3aTotal"]))
    for i in MCIT_ROWS:
        sv(f"txtPg4Sc4I{i}C1", data.get(f"mcit{i}Year"))
        r.p(f"txtPg4Sc4I{i}C2", _n(data.get(f"mcit{i}A")))
        r.p(f"txtPg4Sc4I{i}C3", _n(data.get(f"mcit{i}B")))
        r.p(f"txtPg4Sc4I{i}C4", _n(data.get(f"mcit{i}C")))
    for i in MCIT_ROWS:
        r.p(f"txtPg4Sc4I{i}C5", _n(data.get(f"mcit{i}D")))
        r.p(f"txtPg4Sc4I{i}C6", _n(data.get(f"mcit{i}E")))
        r.p(f"txtPg4Sc4I{i}C7", _n(data.get(f"mcit{i}F")))
        r.p(f"txtPg4Sc4I{i}C8", _n(nv(f"mcit{i}C") - (nv(f"mcit{i}D") + nv(f"mcit{i}E") + nv(f"mcit{i}F"))))
    r.p("txtPg4Sc4I4TotalExcessMCIT", _n(o["sch4Total"]))
    r.p("txtPg4Sc5I1NetIncome", _n(data.get("schV1")))
    for i in (2, 3):
        sv(f"txtPg4Sc5I{i}C1", data.get(f"schV{i}desc"))
        r.p(f"txtPg4Sc5I{i}C2", _n(data.get(f"schV{i}")))
    r.p("txtPg4Sc5I4Total", _n(o["schV4"]))
    for i in (5, 6, 7, 8):
        sv(f"txtPg4Sc5I{i}C1", data.get(f"schV{i}desc"))
        r.p(f"txtPg4Sc5I{i}C2", _n(data.get(f"schV{i}")))
    r.p("txtPg4Sc5I9Total", _n(o["schV9"]))
    r.p("txtPg4Sc5I10NetTaxableIncome", _n(o["schV10"]))
    for k in ("txtPg2Pt4I54CtrModal", "txtPg3Sc1I17iCtrModal", "txtPg3Sc2I4CtrModal", "txtPg4Sc5I3CtrModal", "txtPg4Sc5I6CtrModal", "txtPg4Sc5I8CtrModal"):
        r.p(k, "0")
    r.p("txtCurrentPage", "1")
    r.p("txtMaxPage", "4")
    for k in ("txtPg4Sc3I3Subtotal", "txtPg4Sc4I4Subtotal", "txtPg3Sc1I17iSubtotal", "txtPg3Sc2I4Subtotal", "txtPg4Sc3AI7C2Subtotal", "txtPg4Sc3AI7C3Subtotal", "txtPg4Sc3AI7C4Subtotal", "txtPg4Sc3AI7C5Subtotal", "txtPg4Sc3AI7C6Subtotal", "txtPg2Pt4I54Subtotal", "txtPg4Sc5I3Subtotal", "txtPg4Sc5I6Subtotal", "txtPg4Sc5I8Subtotal"):
        r.p(k, "0")
    r.g("driveSelectTPExport", "0")
    inc.trailer(r, ctx.final)
    fname = f"{t['t1']}{t['t2']}{t['t3']}{t['branch3']}1702RTv2018{mm}{p.year}.xml"
    return r.out, fname


def write_export(rows: list[tuple[str, str]]) -> str:
    return inc.write_1702(rows, "2014.0")


def key_figures(comp: list[dict]) -> dict[str, Decimal]:
    o = inc.payload(comp)
    return {"tax_due": o["i14"], "credits": o["i15"], "payable": o["i21"]}
