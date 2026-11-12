"""BIR Form 1701Q, Quarterly Income Tax Return for Individuals, Estates and Trusts
(January 2018 ENCS). Exported for eBIRForms and printed on the blank.

Two columns, A (the taxpayer) and B (the spouse): every per-column key ends in
A or B. Books (column A, this quarter from the tax engine): salesA, cogsA,
deductA (itemized), prevTaxableA (42), prev8A (50), cwtPrevA (57), cwtA (58),
taxPaidPrevA (59), rateA and methodA from the Company's income-tax option.
Typed: nonOp (43), gpp (44), excess (55), prevPaid (56), foreignCredits (60),
otherCredits (61), surcharge, interest, compromise (64 to 66), atc, sheets,
foreign tax, spouse block, payments. Derived: 38, 39 or 40 (OSD), 41, 45 to 49,
51 to 54, 62, 63, 67, 68, 26 to 31.
"""

from decimal import Decimal

from ph_cas.forms import income as inc
from ph_cas.forms.engine import Context
from ph_cas.forms.export import ExportRefusal, amt, tin_parts
from ph_cas.forms.money import ZERO
from ph_cas.forms.needs import Need, draft_need

NS = "frm1701q:"
SIDES = ("A", "B")


def _side_inputs(side: str) -> list:
    who = "" if side == "A" else " (spouse)"
    return [
        (f"rate{side}", f"Tax rate{who}", "select:graduated,eight"),
        (f"method{side}", f"Method of deduction{who}", "select:osd,itemized"),
        (f"sales{side}", f"36 Sales/revenues/receipts/fees{who}", "money"),
        (f"cogs{side}", f"37 Cost of sales or services{who}", "money"),
        (f"deduct{side}", f"39 Itemized deductions{who}", "money"),
        (f"prevTaxable{side}", f"42 Taxable income previous quarters{who}", "money"),
        (f"nonOp{side}", f"43 Non-operating income{who}", "money"),
        (f"gpp{side}", f"44 Share in GPP net income{who}", "money"),
        (f"prev8{side}", f"50 Sales previous quarters (8% option){who}", "money"),
        (f"excess{side}", f"55 Prior year's excess credits{who}", "money"),
        (f"prevPaid{side}", f"56 Tax payments previous quarters{who}", "money"),
        (f"cwtPrev{side}", f"57 Creditable tax withheld previous quarters{who}", "money"),
        (f"cwt{side}", f"58 Creditable tax withheld per 2307 this quarter{who}", "money"),
        (f"taxPaidPrev{side}", f"59 Tax paid in return previously filed (amended){who}", "money"),
        (f"foreignCredits{side}", f"60 Foreign tax credits{who}", "money"),
        (f"otherCredits{side}", f"61 Other tax credits{who}", "money"),
        (f"surcharge{side}", f"64 Surcharge{who}", "money"),
        (f"interest{side}", f"65 Interest{who}", "money"),
        (f"compromise{side}", f"66 Compromise{who}", "money"),
    ]


INPUTS = (
    [
        ("atc", "8 ATC", "select:II012,II014,II013,II015,II017,II016"),
        ("sheets", "3 Number of sheets attached", "text"),
        ("foreignCredit", "13 Claiming foreign tax credits", "select:no,yes"),
        ("foreignTaxNo", "14 Foreign tax number", "text"),
        ("lineBus", "Line of business (blank: the Company's)", "text"),
        ("nonOpDescA", "43 specify", "text"),
        ("nonOp8DescA", "48 specify", "text"),
        ("otherCreditsDescA", "61 specify", "text"),
    ]
    + _side_inputs("A")
    + _side_inputs("B")
    + inc.SPOUSE_INPUTS
    + inc.PAY_INPUTS
)


def feed(ctx: Context) -> dict:
    company = ctx.company["name"]
    this, prev, _series = inc.quarter_figures(company, ctx)
    c = ctx.company
    eight = (c.get("ph_income_tax_option") or "") == "8% option (individual)"
    osd = (c.get("ph_deduction_method") or "Itemized") != "Itemized"
    figures = {
        "rateA": "eight" if eight else "graduated",
        "methodA": "osd" if osd else "itemized",
        "salesA": inc.peso_text(inc.nonneg_peso(this.get("Sales"))),
        "cogsA": inc.peso_text(inc.nonneg_peso(this.get("COGS"))),
        "prevTaxableA": inc.peso_text(prev.get("Taxable income", ZERO)) if prev else "0",
        "prev8A": inc.peso_text(inc.nonneg_peso(prev.get("Sales"))),
        "cwtPrevA": inc.peso_text(prev.get("Credits 2307", ZERO)) if prev else "0",
        "cwtA": inc.peso_text(this.get("Credits 2307", ZERO)),
        "prevPaidA": inc.peso_text(this.get("Prior quarters", ZERO) + prev.get("Prior quarters", ZERO)),
    }
    if ctx.extra.get("amends"):
        import frappe

        paid = frappe.db.get_value("PH Tax Return Line", {"parent": ctx.extra["amends"], "item": "30/68A"}, "amount") or 0
        figures["taxPaidPrevA"] = inc.peso_text(inc.nonneg_peso(paid))
    if not osd and not eight:
        figures["deductA"] = inc.peso_text(inc.nonneg_peso(this.get("Deductions")))
    start, end = ctx.period.start, ctx.period.end
    lines = [
        inc.books_line("salesA", "Item 36, sales/revenues/receipts/fees this quarter", figures["salesA"], company, start, end),
        inc.books_line("cogsA", "Item 37, cost of sales or services this quarter", figures["cogsA"], company, start, end, "purchase-invoice"),
        inc.books_line("cwtA", "Item 58, creditable tax withheld per 2307 this quarter", figures["cwtA"], company, start, end, "ph-2307-received"),
    ]
    if "deductA" in figures:
        lines.append(inc.books_line("deductA", "Item 39, itemized deductions this quarter", figures["deductA"], company, start, end, "purchase-invoice"))
    warnings = [f"Item {k} ({v}) is below zero in the books; it is shown as 0." for k, v in (("36", this.get("Sales", ZERO)), ("37", this.get("COGS", ZERO))) if v < 0]
    return {"figures": figures, "lines": lines, "warnings": warnings}


def _side(data: dict, s: str, year: int) -> dict[str, Decimal]:
    w = lambda k: inc.w(data, k + s)  # noqa: E731
    o: dict = {}
    o["sales"] = w("sales")
    o["cogs"] = w("cogs")
    o["gross"] = o["sales"] - o["cogs"]
    o["method"] = inc.s(data.get("method" + s)) or "osd"
    o["deductions"] = inc.whole_peso(o["sales"] * Decimal("0.4")) if o["method"] == "osd" else w("deduct")
    o["netIncome"] = o["gross"] - o["deductions"]
    o["prevTaxable"], o["nonOp"], o["gpp"] = w("prevTaxable"), w("nonOp"), w("gpp")
    o["taxableCum"] = o["netIncome"] + o["prevTaxable"] + o["nonOp"] + o["gpp"]
    o["gradTax"] = inc.graduated_tax(o["taxableCum"], year)
    o["sales8"], o["nonOp8"] = o["sales"], o["nonOp"]
    o["income8"] = o["sales8"] + o["nonOp8"]
    o["prev8"] = w("prev8")
    o["cum8"] = o["income8"] + o["prev8"]
    o["reduce8"] = inc.REDUCTION if s == "A" else ZERO
    o["taxable8"] = max(ZERO, o["cum8"] - o["reduce8"])
    o["tax8"] = inc.whole_peso(o["taxable8"] * inc.EIGHT)
    o["rate"] = inc.s(data.get("rate" + s)) or "graduated"
    o["taxDue"] = o["tax8"] if o["rate"] == "eight" else o["gradTax"]
    for k in ("excess", "prevPaid", "cwtPrev", "cwt", "taxPaidPrev", "foreignCredits", "otherCredits"):
        o[k] = w(k)
    o["credits"] = sum((o[k] for k in ("excess", "prevPaid", "cwtPrev", "cwt", "taxPaidPrev", "foreignCredits", "otherCredits")), ZERO)
    o["payable"] = o["taxDue"] - o["credits"]
    o["surcharge"], o["interest"], o["compromise"] = w("surcharge"), w("interest"), w("compromise")
    o["penalties"] = o["surcharge"] + o["interest"] + o["compromise"]
    o["totalPayable"] = o["payable"] + o["penalties"]
    return o


LABELS = [
    ("sales", "36", "Sales/Revenues/Receipts/Fees"), ("cogs", "37", "Less: Cost of Sales/Services"), ("gross", "38", "Gross Income/(Loss) from Operation"),
    ("deductions", "39/40", "Deductions (itemized, or OSD 40% of sales)"), ("netIncome", "41", "Net Income/(Loss) This Quarter"), ("prevTaxable", "42", "Add: Taxable Income/(Loss) Previous Quarters"),
    ("nonOp", "43", "Non-operating Income"), ("gpp", "44", "Share in GPP Net Income"), ("taxableCum", "45", "Total Taxable Income/(Loss) to Date"), ("gradTax", "46", "Tax Due under the Graduated Rates"),
    ("prev8", "50", "Sales Previous Quarters (8% option)"), ("cum8", "51", "Cumulative Sales and Non-operating Income"), ("reduce8", "52", "Less: Allowable Reduction"), ("taxable8", "53", "Taxable Income (8% option)"), ("tax8", "54", "Tax Due (8%)"),
    ("taxDue", "26", "Tax Due"), ("excess", "55", "Prior Year's Excess Credits"), ("prevPaid", "56", "Tax Payments for the Previous Quarters"), ("cwtPrev", "57", "Creditable Tax Withheld for the Previous Quarters"),
    ("cwt", "58", "Creditable Tax Withheld per BIR Form 2307 for this Quarter"), ("taxPaidPrev", "59", "Tax Paid in Return Previously Filed, if Amended"), ("foreignCredits", "60", "Foreign Tax Credits"), ("otherCredits", "61", "Other Tax Credits/Payments"),
    ("credits", "27/62", "Total Tax Credits/Payments"), ("payable", "28/63", "Tax Payable/(Overpayment)"), ("surcharge", "64", "Surcharge"), ("interest", "65", "Interest"), ("compromise", "66", "Compromise"),
    ("penalties", "29/67", "Total Penalties"), ("totalPayable", "30/68", "Total Amount Payable/(Overpayment)"),
]
DERIVED = {"gross", "deductions", "netIncome", "taxableCum", "gradTax", "cum8", "reduce8", "taxable8", "tax8", "taxDue", "credits", "payable", "penalties", "totalPayable"}


def compute(data: dict, ctx: Context) -> list[dict]:
    kind = inc.kinds(data)
    year = ctx.period.year
    sides = {s: _side(data, s, year) for s in SIDES}
    out = []
    for key, item, label in LABELS:
        for s in SIDES:
            if s == "B" and not _has_spouse(data):
                continue
            o = sides[s]
            k = "derived" if key in DERIVED or (key == "deductions" and o["method"] == "osd") else kind(("deduct" if key == "deductions" else key) + s)
            out.append(inc.line(f"{item}{s}", f"{label} ({'taxpayer' if s == 'A' else 'spouse'})", o[key], k))
    aggregate = sides["A"]["totalPayable"] + (sides["B"]["totalPayable"] if _has_spouse(data) else ZERO)
    out.append(inc.line("31", "Aggregate Amount Payable/(Overpayment)", aggregate, "derived"))
    out.append(inc.hidden("_c", {"A": sides["A"], "B": sides["B"], "aggregate": aggregate}))
    return out


def _has_spouse(data: dict) -> bool:
    return any(inc.s(data.get(k)) for k in ("rateB", "methodB", "spouseName", "spouseTin", "salesB"))


def needs(data: dict, ctx: Context) -> list[Need]:
    out = inc.common_needs(data, ctx, "1701Q", False)
    if inc.s(data.get("methodA")) == "itemized" and inc.s(data.get("rateA")) != "eight" and not inc.s(data.get("deductA")):
        out.append(draft_need(ctx.return_name, "deductA", "What are the itemized deductions for the quarter (Item 39)?", "The itemized method needs the figure; the books feed it when expenses are posted.", "money"))
    return out


def export_rows(data: dict, comp: list[dict], ctx: Context) -> tuple[list[tuple[str, str]], str]:
    c = ctx.company
    cp = inc.payload(comp)
    A, B = cp["A"], cp["B"]
    t = inc.tin(c)
    p = ctx.period
    qn = p.quarter_no
    if qn == 4:
        raise ExportRefusal("The 1701Q covers the first three quarters; the fourth quarter is reported in the annual return.")
    atc = inc.chosen_atc(data.get("atc"), "1701Q")
    ttype = inc.taxpayer_type(c)
    has_spouse = _has_spouse(data)
    r = inc.Rows(NS)
    r.p("txtYear", str(p.year))
    for n in (1, 2, 3):
        r.b(f"DateQuarter_{n}", qn == n)
    r.b("AmendedRtn_1", ctx.is_amended)
    r.b("AmendedRtn_2", not ctx.is_amended)
    r.p("txtSheets", inc.s(data.get("sheets")) or "0")
    r.p("txtTIN1", t["t1"])
    r.p("txtTIN2", t["t2"])
    r.p("txtTIN3", t["t3"])
    r.p("txtBranchCode", t["branch3"])
    r.p("txtRDOCode", c.get("ph_rdo") or "")
    r.b("optType_1", ttype == "single")
    r.b("optType_2", ttype == "prof")
    r.b("optType_3", False)
    r.b("optType_4", False)
    for n, code in enumerate(inc.ATC["1701Q"], start=1):
        r.b(f"optATC_{n}", atc == code)
    r.enc("txtTaxpayerName", inc.name_commas(c))
    r.enc("txtAddress", inc.address(c))
    r.p("txtZipCode", c.get("ph_zip") or "")
    mm, dd, yyyy = inc.birth_parts(c.get("ph_birthdate"))
    r.p("txtBirthMonth", mm)
    r.p("txtBirthDay", dd)
    r.p("txtBirthYear", yyyy)
    r.g("txtEmail", c.get("ph_email") or "")
    r.p("txtCitizenship", c.get("ph_citizenship") or "")
    r.enc("txtForeignTaxNumber", data.get("foreignTaxNo"))
    fc = inc.s(data.get("foreignCredit")) == "yes"
    r.b("optForeignTaxCredits_1", fc)
    r.b("optForeignTaxCredits_2", not fc)
    r.b("optTaxRate_1", A["rate"] != "eight")
    r.b("optMethodOfDeduction:_1", inc.s(data.get("methodA")) == "itemized")
    r.b("optMethodOfDeduction:_2", inc.s(data.get("methodA")) == "osd")
    r.b("optTaxRate_2", A["rate"] == "eight")
    stin = inc.spouse_tin(data)
    r.p("txtSpouseTIN1", stin[0:3])
    r.p("txtSpouseTIN2", stin[3:6])
    r.p("txtSpouseTIN3", stin[6:9])
    r.p("txtSpouseBranchCode", "000" if stin else "")
    r.p("txtSpouseRDOCode", inc.s(data.get("spouseRdo")) or "000")
    st = inc.s(data.get("spouseType"))
    r.b("optSpouseType_1", st == "single")
    r.b("optSpouseType_2", st == "prof")
    r.b("optSpouseType_3", st == "comp")
    satc = inc.s(data.get("spouseAtc")).upper()
    for n, code in enumerate(("II012", "II014", "II013", "II011", "II015", "II017", "II016"), start=1):
        r.b(f"optSpouseATC_{n}", satc == code)
    r.enc("txtSpouseName", data.get("spouseName"))
    r.enc("txtSpouseCitizenship", data.get("spouseCitizenship"))
    r.enc("txtSpouseForeignTaxNum", data.get("spouseForeignTaxNo"))
    sfc = inc.s(data.get("spouseForeignCredit")) == "yes"
    r.b("optSpouseForeignTaxCred_1", has_spouse and sfc)
    r.b("optSpouseForeignTaxCred_2", has_spouse and not sfc)
    r.b("optSpouseTaxRate_1", has_spouse and B["rate"] != "eight")
    r.b("optSpouseMethod:_1", inc.s(data.get("methodB")) == "itemized")
    r.b("optSpouseMethod:_2", inc.s(data.get("methodB")) == "osd")
    r.b("optSpouseTaxRate_2", has_spouse and B["rate"] == "eight")
    for item, key in ((26, "taxDue"), (27, "credits"), (28, "payable"), (29, "penalties"), (30, "totalPayable")):
        r.a(f"txt{item}A", A[key])
        r.a(f"txt{item}B", B[key] if has_spouse else 0)
    r.a("txt31", cp["aggregate"])
    inc.payments(r, data)
    r.p("txtPg2TIN1", t["t1"])
    r.p("txtPg2TIN2", t["t2"])
    r.p("txtPg2TIN3", t["t3"])
    r.p("txtPg2BranchCode", t["branch3"])
    r.p("txtPg2TaxpayerName", inc.name_raw(c))
    side = lambda o: {  # noqa: E731
        36: o["sales"], 37: o["cogs"], 38: o["gross"], 39: ZERO if o["method"] == "osd" else o["deductions"], 40: o["deductions"] if o["method"] == "osd" else ZERO,
        41: o["netIncome"], 42: o["prevTaxable"], 43: o["nonOp"], 44: o["gpp"], 45: o["taxableCum"], 46: o["gradTax"],
        47: o["sales8"], 48: o["nonOp8"], 49: o["income8"], 50: o["prev8"], 51: o["cum8"], 52: o["reduce8"], 53: o["taxable8"], 54: o["tax8"],
        55: o["excess"], 56: o["prevPaid"], 57: o["cwtPrev"], 58: o["cwt"], 59: o["taxPaidPrev"], 60: o["foreignCredits"], 61: o["otherCredits"], 62: o["credits"],
        63: o["payable"], 64: o["surcharge"], 65: o["interest"], 66: o["compromise"], 67: o["penalties"], 68: o["totalPayable"],
    }
    ma, mb = side(A), side(B)
    desc = {43: "nonOpDescA", 48: "nonOp8DescA", 61: "otherCreditsDescA"}
    for i in range(36, 69):
        if i in desc:
            r.enc(f"txt{i}Desc", data.get(desc[i]))
        r.a(f"txt{i}A", ma[i])
        r.a(f"txt{i}B", mb[i] if has_spouse else 0)
    r.p("txtCurrentPage", "1")
    r.p("txtMaxPage", "2")
    inc.trailer(r, ctx.final)
    r.enc("txtLOB", inc.s(data.get("lineBus")) or c.get("ph_line_of_business"))
    r.p("txtTelno", ctx.contact_number or c.get("ph_contact_number") or "")
    r.g("driveSelectTPExport", "0")
    name = f"{t['t1']}{t['t2']}{t['t3']}{t['branch3']}1701Qv2018{p.year}Q{qn}.xml"
    return r.out, name


def write_export(rows: list[tuple[str, str]]) -> str:
    return inc.write_1701q(rows)


def key_figures(comp: list[dict]) -> dict[str, Decimal]:
    c = inc.payload(comp)
    return {"tax_due": c["A"]["taxDue"], "credits": c["A"]["credits"], "payable": c["aggregate"]}


__all__ = ["INPUTS", "LABELS", "compute", "export_rows", "feed", "key_figures", "needs", "write_export", "amt", "tin_parts"]
