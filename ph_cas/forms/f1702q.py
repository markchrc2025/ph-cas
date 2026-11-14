"""BIR Form 1702Q, Quarterly Income Tax Return for Corporations, Partnerships and
Other Non-Individual Taxpayers (January 2018 ENCS). Exported for eBIRForms and
printed on the blank. Whole pesos.

Books (this quarter, from the tax engine): s2_1 sales, s2_2 cost of sales,
s2_6 deductions (itemized), s2_8 taxable income previous quarters, sch3_1 to
sch3_3 gross income per quarter (MCIT base), sch4_2 tax payments previous
quarters, sch4_4 creditable tax withheld previous quarters, sch4_5 creditable
tax withheld this quarter, rate and method from the Company, mcit yes or no
from the Company's year of operations start.
Typed: s2_4 non-operating income, sch1_* (exempt and special columns),
sch1Rate, sch4_1, sch4_3, sch4_6, sch4_6a, sch4_6b, i15, i21 to i23, treaty,
atc, attachments, lineBus. Derived: the rest.
"""

from decimal import Decimal

from ph_cas.forms import income as inc
from ph_cas.forms.engine import Context
from ph_cas.forms.export import ExportRefusal
from ph_cas.forms.money import ZERO
from ph_cas.forms.needs import Need

NS = "frm1702q:"
INPUTS = [
    ("atc", "5 ATC", "select:IC055"),
    ("rate", "Income tax rate % (25, or 20 for small corporations)", "text"),
    ("method", "Method of deduction", "select:itemized,osd"),
    ("mcit", "Minimum corporate income tax applies (4th year onward)", "select:yes,no"),
    ("attachments", "Number of sheets attached", "text"),
    ("treaty", "Availing of tax treaty relief", "select:no,yes"),
    ("lineBus", "Description of business (blank: the Company's line of business)", "text"),
    ("s2_1", "Sch 2 Item 1 Sales/revenues/receipts/fees this quarter", "money"),
    ("s2_2", "Sch 2 Item 2 Cost of sales or services", "money"),
    ("s2_4", "Sch 2 Item 4 Non-operating and other taxable income", "money"),
    ("s2_6", "Sch 2 Item 6 Itemized deductions", "money"),
    ("s2_8", "Sch 2 Item 8 Taxable income previous quarters", "money"),
    ("sch1Rate", "Sch 1 special rate %", "text"),
    ("sch1_1A", "Sch 1 Exempt: sales", "money"),
    ("sch1_2A", "Sch 1 Exempt: cost of sales", "money"),
    ("sch1_4A", "Sch 1 Exempt: other income", "money"),
    ("sch1_6A", "Sch 1 Exempt: deductions", "money"),
    ("sch1_8A", "Sch 1 Exempt: taxable income previous quarters", "money"),
    ("sch1_12A", "Sch 1 Exempt: less share of other agencies", "money"),
    ("sch1_1B", "Sch 1 Special: sales", "money"),
    ("sch1_2B", "Sch 1 Special: cost of sales", "money"),
    ("sch1_4B", "Sch 1 Special: other income", "money"),
    ("sch1_6B", "Sch 1 Special: deductions", "money"),
    ("sch1_8B", "Sch 1 Special: taxable income previous quarters", "money"),
    ("sch1_12B", "Sch 1 Special: less share of other agencies", "money"),
    ("sch3_1", "Sch 3 gross income 1st quarter (MCIT)", "money"),
    ("sch3_2", "Sch 3 gross income 2nd quarter (MCIT)", "money"),
    ("sch3_3", "Sch 3 gross income 3rd quarter (MCIT)", "money"),
    ("sch4_1", "Sch 4 Item 1 Prior year's excess credits", "money"),
    ("sch4_2", "Sch 4 Item 2 Tax payments previous quarters (other than MCIT)", "money"),
    ("sch4_3", "Sch 4 Item 3 MCIT payments previous quarters", "money"),
    ("sch4_4", "Sch 4 Item 4 Creditable tax withheld previous quarters", "money"),
    ("sch4_5", "Sch 4 Item 5 Creditable tax withheld per 2307 this quarter", "money"),
    ("sch4_6", "Sch 4 Item 6 Tax paid in return previously filed (amended)", "money"),
    ("sch4_6a", "Sch 4 Item 6a Other credits", "money"),
    ("sch4_6b", "Sch 4 Item 6b Other credits", "money"),
    ("i15", "15 Unexpired excess of prior year's MCIT over normal tax", "money"),
    ("i21", "21 Surcharge", "money"),
    ("i22", "22 Interest", "money"),
    ("i23", "23 Compromise", "money"),
]


def feed(ctx: Context) -> dict:
    company = ctx.company["name"]
    c = ctx.company
    this, prev, series = inc.quarter_figures(company, ctx)
    osd = (c.get("ph_deduction_method") or "Itemized") != "Itemized"
    year = ctx.period.year
    start_year = c.get("ph_operations_start_year")
    figures = {
        "rate": "20" if c.get("ph_corp_small") else "25",
        "method": "osd" if osd else "itemized",
        "mcit": "yes" if start_year and year >= int(start_year) + 4 else "no",
        "s2_1": inc.peso_text(inc.nonneg_peso(this.get("Sales"))),
        "s2_2": inc.peso_text(inc.nonneg_peso(this.get("COGS"))),
        "s2_8": inc.peso_text(prev.get("Taxable income", ZERO)) if prev else "0",
        "sch4_2": inc.peso_text(this.get("Prior quarters", ZERO) + prev.get("Prior quarters", ZERO)),
        "sch4_4": inc.peso_text(prev.get("Credits 2307", ZERO)) if prev else "0",
        "sch4_5": inc.peso_text(this.get("Credits 2307", ZERO)),
    }
    if not osd:
        figures["s2_6"] = inc.peso_text(inc.nonneg_peso(this.get("Deductions")))
    for n, own in enumerate(series, start=1):
        if n <= 3:
            figures[f"sch3_{n}"] = inc.peso_text(inc.nonneg_peso(own.get("Gross income")))
    if ctx.extra.get("amends"):
        import frappe

        paid = frappe.db.get_value("PH Tax Return Line", {"parent": ctx.extra["amends"], "item": "25"}, "amount") or 0
        figures["sch4_6"] = inc.peso_text(inc.nonneg_peso(paid))
    start, end = ctx.period.start, ctx.period.end
    lines = [
        inc.books_line("s2_1", "Schedule 2 Item 1, sales this quarter", figures["s2_1"], company, start, end),
        inc.books_line("s2_2", "Schedule 2 Item 2, cost of sales this quarter", figures["s2_2"], company, start, end, "purchase-invoice"),
        inc.books_line("sch4_5", "Schedule 4 Item 5, creditable tax withheld this quarter", figures["sch4_5"], company, start, end, "ph-2307-received"),
    ]
    if "s2_6" in figures:
        lines.append(inc.books_line("s2_6", "Schedule 2 Item 6, itemized deductions this quarter", figures["s2_6"], company, start, end, "purchase-invoice"))
    warnings = [f"Schedule 2 Item {i} ({v}) is below zero in the books; it is shown as 0." for i, v in (("1", this.get("Sales", ZERO)), ("2", this.get("COGS", ZERO))) if v < 0]
    return {"figures": figures, "lines": lines, "warnings": warnings}


def _compute(data: dict, ctx: Context) -> dict:
    w = lambda k: inc.w(data, k)  # noqa: E731
    o: dict = {}
    rate = inc.dec(data.get("rate")) if inc.s(data.get("rate")) else Decimal(25)
    o["rate"] = rate
    o["sch1Rate"] = inc.dec(data.get("sch1Rate")) if inc.s(data.get("sch1Rate")) else ZERO
    for col in "AB":
        o[f"sch1_1{col}"], o[f"sch1_2{col}"] = w(f"sch1_1{col}"), w(f"sch1_2{col}")
        o[f"sch1_3{col}"] = o[f"sch1_1{col}"] - o[f"sch1_2{col}"]
        o[f"sch1_4{col}"] = w(f"sch1_4{col}")
        o[f"sch1_5{col}"] = o[f"sch1_3{col}"] + o[f"sch1_4{col}"]
        o[f"sch1_6{col}"] = w(f"sch1_6{col}")
        o[f"sch1_7{col}"] = o[f"sch1_5{col}"] - o[f"sch1_6{col}"]
        o[f"sch1_8{col}"] = w(f"sch1_8{col}")
        o[f"sch1_9{col}"] = o[f"sch1_7{col}"] + o[f"sch1_8{col}"]
        o[f"sch1_11{col}"] = ZERO if col == "A" else inc.whole_peso(o["sch1_9B"] * o["sch1Rate"] / 100)
        o[f"sch1_12{col}"] = w(f"sch1_12{col}")
        o[f"sch1_13{col}"] = o[f"sch1_11{col}"] - o[f"sch1_12{col}"]
    o["sch1_13"] = o["sch1_13A"] + o["sch1_13B"]
    o["s2_1"], o["s2_2"] = w("s2_1"), w("s2_2")
    o["s2_3"] = o["s2_1"] - o["s2_2"]
    o["s2_4"] = w("s2_4")
    o["s2_5"] = o["s2_3"] + o["s2_4"]
    o["method"] = inc.s(data.get("method")) or "itemized"
    o["s2_6"] = inc.whole_peso(o["s2_5"] * Decimal("0.4")) if o["method"] == "osd" else w("s2_6")
    o["s2_7"] = o["s2_5"] - o["s2_6"]
    o["s2_8"] = w("s2_8")
    o["s2_9"] = o["s2_7"] + o["s2_8"]
    o["s2_10"] = rate
    o["s2_11"] = inc.whole_peso(o["s2_9"] * rate / 100)
    qn = ctx.period.quarter_no
    for n in (1, 2, 3):
        o[f"sch3_{n}"] = w(f"sch3_{n}") or (o["s2_5"] if qn == n else ZERO)
    o["sch3_4"] = o["sch3_1"] + o["sch3_2"] + o["sch3_3"]
    mcit_on = (inc.s(data.get("mcit")) or "yes") == "yes"
    base = o["sch3_4"] if o["sch3_4"] > 0 else o["s2_5"]
    o["sch3_6"] = inc.whole_peso(base * Decimal("0.02")) if mcit_on else ZERO
    o["mcit"] = o["sch3_6"]
    o["s2_13"] = max(o["s2_11"], o["mcit"])
    o["mcitApplies"] = o["mcit"] > o["s2_11"]
    for k in ("sch4_1", "sch4_2", "sch4_3", "sch4_4", "sch4_5", "sch4_6", "sch4_6a", "sch4_6b"):
        o[k] = w(k)
    o["sch4_7"] = sum((o[k] for k in ("sch4_1", "sch4_2", "sch4_3", "sch4_4", "sch4_5", "sch4_6", "sch4_6a", "sch4_6b")), ZERO)
    o["i14"] = o["s2_13"]
    o["i15"] = w("i15")
    o["i16"] = o["i14"] - o["i15"]
    o["i17"] = o["sch1_13"]
    o["i18"] = o["i16"] + o["i17"]
    o["i19"] = o["sch4_7"]
    o["i20"] = o["i18"] - o["i19"]
    o["i21"], o["i22"], o["i23"] = w("i21"), w("i22"), w("i23")
    o["i24"] = o["i21"] + o["i22"] + o["i23"]
    o["i25"] = o["i20"] + o["i24"]
    return o


LABELS = [
    ("s2_1", "Sch 2.1", "Sales/Revenues/Receipts/Fees"), ("s2_2", "Sch 2.2", "Less: Cost of Sales/Services"), ("s2_3", "Sch 2.3", "Gross Income from Operation"), ("s2_4", "Sch 2.4", "Add: Non-operating and Other Taxable Income"),
    ("s2_5", "Sch 2.5", "Total Gross Income"), ("s2_6", "Sch 2.6", "Less: Deductions"), ("s2_7", "Sch 2.7", "Taxable Income this Quarter"), ("s2_8", "Sch 2.8", "Add: Taxable Income Previous Quarters"),
    ("s2_9", "Sch 2.9", "Total Taxable Income to Date"), ("s2_11", "Sch 2.11", "Income Tax Due (regular rate)"), ("mcit", "Sch 2.12", "Minimum Corporate Income Tax (2% of gross income)"), ("s2_13", "Sch 2.13", "Income Tax Due (higher of 11 and 12)"),
    ("sch1_13", "Sch 1.13", "Net Income Tax Due, exempt and special"), ("i14", "14", "Income Tax Due, Regular Rate"), ("i15", "15", "Less: Unexpired Excess of Prior Year's MCIT"), ("i16", "16", "Balance Income Tax Still Due, Regular Rate"),
    ("i17", "17", "Add: Income Tax Due, Special Rate"), ("i18", "18", "Aggregate Income Tax Due"), ("sch4_1", "Sch 4.1", "Prior Year's Excess Credits"), ("sch4_2", "Sch 4.2", "Tax Payments for the Previous Quarters (other than MCIT)"),
    ("sch4_3", "Sch 4.3", "MCIT Payments for the Previous Quarters"), ("sch4_4", "Sch 4.4", "Creditable Tax Withheld for the Previous Quarters"), ("sch4_5", "Sch 4.5", "Creditable Tax Withheld per BIR Form 2307 for this Quarter"), ("sch4_6", "Sch 4.6", "Tax Paid in Return Previously Filed, if Amended"),
    ("sch4_6a", "Sch 4.6a", "Other Tax Credits/Payments"), ("sch4_6b", "Sch 4.6b", "Other Tax Credits/Payments"), ("i19", "19", "Less: Total Tax Credits/Payments"), ("i20", "20", "Net Tax Payable/(Overpayment)"),
    ("i21", "21", "Surcharge"), ("i22", "22", "Interest"), ("i23", "23", "Compromise"), ("i24", "24", "Total Penalties"), ("i25", "25", "TOTAL AMOUNT PAYABLE/(Overpayment)"),
]
DERIVED = {"s2_3", "s2_5", "s2_7", "s2_9", "s2_11", "mcit", "s2_13", "sch1_13", "i14", "i16", "i17", "i18", "i19", "i20", "i24", "i25"}


def compute(data: dict, ctx: Context) -> list[dict]:
    kind = inc.kinds(data)
    o = _compute(data, ctx)
    out = []
    for key, item, label in LABELS:
        k = "derived" if key in DERIVED or (key == "s2_6" and o["method"] == "osd") else kind(key)
        out.append(inc.line(item, label, o[key], k))
    out.append(inc.hidden("_c", o))
    return out


def needs(data: dict, ctx: Context) -> list[Need]:
    return inc.common_needs(data, ctx, "1702Q", False)


def export_rows(data: dict, comp: list[dict], ctx: Context) -> tuple[list[tuple[str, str]], str]:
    c = ctx.company
    o = inc.payload(comp)
    t = inc.tin(c)
    p = ctx.period
    qn = p.quarter_no
    if qn == 4:
        raise ExportRefusal("The 1702Q covers the first three quarters; the fourth quarter is reported in the annual return.")
    atc = inc.chosen_atc(data.get("atc"), "1702Q")
    itemized = o["method"] != "osd"
    r = inc.Rows(NS)
    r.b("itemFiscalStartMonth:_1", not p.fiscal)
    r.b("itemFiscalStartMonth:_2", p.fiscal)
    for n in (1, 2, 3):
        r.b(f"optQtr:_{n}", qn == n)
    r.b("optRemenderRtn_1", ctx.is_amended)
    r.b("optRemenderRtn_2", not ctx.is_amended)
    r.p("txtSheets", inc.s(data.get("attachments")) or "0")
    end_month = 12
    if p.fiscal:
        from ph_cas.forms.period import fiscal_start_month

        sm = fiscal_start_month(c.get("ph_fiscal_year_start"))
        end_month = sm - 1 if sm > 1 else 12
    r.p("itemYearEndMonth", f"{end_month:02d}" if p.fiscal else "12")
    r.p("txtYearEnded", str(p.year))
    r.p("txtTin1", t["t1"])
    r.p("txtTin2", t["t2"])
    r.p("txtTin3", t["t3"])
    r.p("txtBranchCode", t["branch3"])
    r.p("txtRdoCode", c.get("ph_rdo") or "")
    r.enc("txtDescription", inc.s(data.get("lineBus")) or c.get("ph_line_of_business"))
    r.enc("txtTaxpayerName", inc.name_reg(c))
    r.p("txtTelNum", ctx.contact_number or c.get("ph_contact_number") or "")
    r.enc("txtTaxPayerAdd", inc.address(c))
    r.p("txtTaxPayerZip", c.get("ph_zip") or "")
    r.g("1702q:OptMethodDeduct_1", "true" if itemized else "false")
    r.g("1702q:OptMethodDeduct_2", "false" if itemized else "true")
    treaty = inc.s(data.get("treaty")) == "yes"
    r.b("optTreaty:_1", treaty)
    r.b("optTreaty:_2", not treaty)
    r.p("lstTaxTreaty", "0")
    r.p("txtAtc", atc)
    r.a("txt16A", o["sch1_1A"])
    r.a("txt16B", o["sch1_1B"])
    r.z("txt16C")
    r.a("txt17A", o["sch1_2A"])
    r.a("txt17B", o["sch1_2B"])
    r.z("txt17C")
    r.a("txt18A", o["sch1_3A"])
    r.a("txt18B", o["sch1_3B"])
    r.z("txt18C")
    r.a("txt19A", o["sch1_4A"])
    r.a("txt19B", o["sch1_4B"])
    r.a("txt20A", o["sch1_5A"])
    r.a("txt20B", o["sch1_5B"])
    r.z("txt20C")
    r.a("txt21A", o["sch1_6A"])
    r.a("txt21B", o["sch1_6B"])
    r.z("txt21C")
    r.a("txt22A", o["sch1_7A"])
    r.a("txt22B", o["sch1_7B"])
    r.a("txt23A", o["sch1_9A"])
    r.a("txt23B", o["sch1_9B"])
    r.a("txt24A", o["sch1_13A"])
    r.a("txt24B", o["sch1_13B"])
    r.a("txt25A", o["sch1Rate"])
    r.a("txt25B", o["rate"])
    r.a("txt26A", o["i14"])
    r.a("txt26B", o["i15"])
    r.a("txt27", o["i16"])
    r.a("txt28", o["i17"])
    r.a("txt29A", o["sch4_1"])
    r.a("txt29B", o["sch4_2"])
    r.a("txt29C", o["sch4_3"])
    r.a("txt29D", o["sch4_4"])
    r.a("txt30", o["i18"])
    r.a("txt31A", o["sch4_5"])
    r.a("txt31B", o["sch4_6"])
    r.a("txt31C", o["sch4_6a"])
    r.a("txt31D", o["sch4_6b"])
    r.a("txt31E", o["sch4_7"])
    r.a("txt31F", o["i20"])
    r.p("txt31Gothers", "")
    r.a("txt31G", o["i21"])
    r.a("txt31H", o["i22"])
    r.a("txt32", o["i23"])
    r.a("txt33A", o["i24"])
    r.z("txt33B")
    r.z("txt33C")
    r.z("txt33D")
    r.a("txt34", o["i25"])
    for i in range(1, 19):
        r.g(f"Codename{i}", "true" if i == 1 else "false")
    r.g("txt1stQtr", inc.amt(o["sch3_1"]))
    r.g("txt2ndQtr", inc.amt(o["sch3_2"]))
    r.g("txt3rdQtr", inc.amt(o["sch3_3"]))
    r.g("txtTotal", inc.amt(o["sch3_4"]))
    r.g("txtTaxRate", "2%")
    r.g("txtMinCorpIncomeTax", inc.amt(o["mcit"]))
    inc.trailer(r, ctx.final)
    r.g("txtEmail", c.get("ph_email") or "")
    r.g("driveSelectTPExport", "0")
    name = f"{t['t1']}{t['t2']}{t['t3']}{t['branch3']}1702Q{p.year}Q{qn}.xml"
    return r.out, name


def write_export(rows: list[tuple[str, str]]) -> str:
    return inc.write_1702(rows, "2012.0")


def key_figures(comp: list[dict]) -> dict[str, Decimal]:
    o = inc.payload(comp)
    return {"tax_due": o["i18"], "credits": o["i19"], "payable": o["i25"]}
