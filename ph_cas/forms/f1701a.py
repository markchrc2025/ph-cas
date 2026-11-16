"""BIR Form 1701A, Annual Income Tax Return for Individuals Earning Income Purely
from Business/Profession (January 2018 ENCS). Exported for eBIRForms and
printed on the blank. Whole pesos. Optional standard deduction or the 8% option
only (the itemized method files the 1701).

Two columns, A (taxpayer) and B (spouse); per-column keys end in A or B.
Books (column A, the year from the tax engine): i36 sales (graduated), i47
sales (8% option), i58 tax payments for the first three quarters, i59
creditable tax withheld for the first three quarters, i60 creditable tax
withheld for the fourth quarter; taxRate from the Company's option.
Typed: i37 and i48 returns, i41 to i43 and i50, i51 other income, i57, i61 to
i63 credits, i23 second installment, i25 to i27 penalties, atc, over,
attachments, spouse block, payments. Derived: the rest.
"""

from decimal import Decimal

from ph_cas.forms import income as inc
from ph_cas.forms.engine import Context
from ph_cas.forms.export import dob
from ph_cas.forms.money import ZERO
from ph_cas.forms.needs import Need

NS = "frm1701A:"
SIDES = ("A", "B")
TYPED = {
    "36": "Sales/Revenues/Receipts/Fees", "37": "Less: Sales Returns, Allowances and Discounts", "41": "Other Non-operating Income (specify)", "42": "Other Non-operating Income (specify)", "43": "Other Taxable Income",
    "47": "Sales/Revenues/Receipts/Fees (8% option)", "48": "Less: Sales Returns, Allowances and Discounts (8% option)", "50": "Other Non-operating Income (specify)", "51": "Other Non-operating Income (specify)",
    "57": "Prior Year's Excess Credits", "58": "Tax Payments for the First Three Quarters", "59": "Creditable Tax Withheld for the First Three Quarters", "60": "Creditable Tax Withheld per BIR Form 2307 for the Fourth Quarter",
    "61": "Tax Paid in Return Previously Filed, if Amended", "62": "Foreign Tax Credits", "63": "Other Tax Credits/Payments (specify)", "23": "Less: Portion of Tax Payable Allowed for Second Installment", "25": "Surcharge", "26": "Interest", "27": "Compromise",
}
DERIVED = {
    "38": "Net Sales/Revenues/Receipts/Fees", "39": "Less: Optional Standard Deduction (40%)", "40": "Net Income", "44": "Total Other Taxable Income", "45": "Total Taxable Income", "46": "Tax Due (graduated rates)",
    "49": "Net Sales (8% option)", "52": "Total Other Non-operating Income", "53": "Total Taxable Income (8% option)", "54": "Less: Allowable Reduction", "55": "Taxable Income (8% option)", "56": "Tax Due (8%)",
    "64": "Total Tax Credits/Payments", "65": "Net Tax Payable/(Overpayment)", "20": "Tax Due", "21": "Less: Total Tax Credits/Payments", "22": "Net Tax Payable/(Overpayment)", "24": "Amount Payable/(Overpayment)", "28": "Total Penalties", "29": "Total Amount Payable/(Overpayment)",
}
ORDER = ["36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "20", "57", "58", "59", "60", "61", "62", "63", "64", "65", "21", "22", "23", "24", "25", "26", "27", "28", "29"]


def _side_inputs(side: str) -> list:
    who = "" if side == "A" else " (spouse)"
    return [(f"i{i}{side}", f"{i} {TYPED[i]}{who}", "money") for i in ("36", "37", "41", "42", "43", "47", "48", "50", "51", "57", "58", "59", "60", "61", "62", "63", "23", "25", "26", "27")]


INPUTS = (
    [
        ("taxRate", "Tax rate", "select:graduated,eight"),
        ("atc", "7 ATC", "select:II012,II014,II015,II017"),
        ("over", "Overpayment: refund, TCC or carry over", "select:refund,tcc,carry"),
        ("attachments", "Number of attachments", "text"),
        ("shortPeriod", "Short period return", "select:no,yes"),
        ("spouseIncome", "17 Spouse has income (married)", "select:yes,no"),
        ("filing", "18 Filing status (married)", "select:joint,separate"),
        ("foreignCredit", "Claiming foreign tax credits", "select:no,yes"),
        ("foreignTaxNo", "Foreign tax number", "text"),
        ("lineBus", "Line of business (blank: the Company's)", "text"),
        ("i41label", "41 specify", "text"),
        ("i42label", "42 specify", "text"),
        ("i50label", "50 specify", "text"),
        ("i51label", "51 specify", "text"),
        ("i63label", "63 specify", "text"),
        ("spouseTaxRate", "Spouse: tax rate", "select:graduated,eight"),
    ]
    + _side_inputs("A")
    + _side_inputs("B")
    + inc.SPOUSE_INPUTS
    + inc.PAY_INPUTS
)


def feed(ctx: Context) -> dict:
    company = ctx.company["name"]
    c = ctx.company
    p = ctx.period
    annual_figs = inc.annual(company, p.start, p.end)
    from ph_cas.forms.period import quarter_range

    q3_end = quarter_range(p.year, 3)[1]
    through_q3 = inc._engine(company, p.start, q3_end, annual=False) if q3_end > p.start else {}
    eight = (c.get("ph_income_tax_option") or "") == "8% option (individual)"
    sales = inc.nonneg_peso(annual_figs.get("Sales"))
    credits = annual_figs.get("Credits 2307", ZERO)
    credits_q3 = through_q3.get("Credits 2307", ZERO)
    figures = {
        "taxRate": "eight" if eight else "graduated",
        "i36A": inc.peso_text(sales),
        "i47A": inc.peso_text(sales),
        "i58A": inc.peso_text(annual_figs.get("Prior quarters", ZERO)),
        "i59A": inc.peso_text(credits_q3),
        "i60A": inc.peso_text(credits - credits_q3),
    }
    if ctx.extra.get("amends"):
        import frappe

        paid = frappe.db.get_value("PH Tax Return Line", {"parent": ctx.extra["amends"], "item": "29A"}, "amount") or 0
        figures["i61A"] = inc.peso_text(inc.nonneg_peso(paid))
    lines = [
        inc.books_line("i36A", "Item 36, sales/revenues/receipts/fees for the year", figures["i36A"], company, p.start, p.end),
        inc.books_line("i58A", "Item 58, tax payments for the first three quarters (filed 1701Q returns)", figures["i58A"], company, p.start, p.end, "ph-tax-return"),
        inc.books_line("i60A", "Item 60, creditable tax withheld per 2307 for the fourth quarter", figures["i60A"], company, p.start, p.end, "ph-2307-received"),
    ]
    warnings = [] if annual_figs.get("Sales", ZERO) >= 0 else ["Item 36 is below zero in the books; it is shown as 0."]
    if (c.get("ph_deduction_method") or "Itemized") == "Itemized" and not eight:
        warnings.append("The Company uses itemized deductions; the 1701A allows only the optional standard deduction or the 8% option. File the 1701 instead, or change the method.")
    return {"figures": figures, "lines": lines, "warnings": warnings}


def _side(data: dict, s: str, year: int, rate: str) -> dict[str, Decimal]:
    w = lambda i: inc.w(data, f"i{i}{s}")  # noqa: E731
    o: dict = {}
    o["36"], o["37"] = w(36), w(37)
    o["38"] = o["36"] - o["37"]
    o["39"] = inc.whole_peso(o["38"] * Decimal("0.4"))
    o["40"] = o["38"] - o["39"]
    o["41"], o["42"], o["43"] = w(41), w(42), w(43)
    o["44"] = o["41"] + o["42"] + o["43"]
    o["45"] = o["40"] + o["44"]
    o["46"] = inc.graduated_tax(o["45"], year)
    o["47"], o["48"] = w(47), w(48)
    o["49"] = o["47"] - o["48"]
    o["50"], o["51"] = w(50), w(51)
    o["52"] = o["50"] + o["51"]
    o["53"] = o["49"] + o["52"]
    o["54"] = inc.REDUCTION
    o["55"] = max(ZERO, o["53"] - o["54"])
    o["56"] = inc.whole_peso(o["55"] * inc.EIGHT)
    # eBIRForms fills only the schedule of the rate the ATC sets: Part IV.A (graduated,
    # Items 36 to 46) or Part IV.B (8%, Items 47 to 56)
    for i in (range(36, 47) if rate == "eight" else range(47, 57)):
        o[str(i)] = ZERO
    o["20"] = o["56"] if rate == "eight" else o["46"]
    for i in range(57, 64):
        o[str(i)] = w(i)
    o["64"] = sum((o[str(i)] for i in range(57, 64)), ZERO)
    o["65"] = o["20"] - o["64"]
    o["21"] = o["64"]
    o["22"] = o["20"] - o["21"]
    o["23"] = w(23)
    o["24"] = o["22"] - o["23"]
    o["25"], o["26"], o["27"] = w(25), w(26), w(27)
    o["28"] = o["25"] + o["26"] + o["27"]
    # eBIRForms (1701A): on an overpayment (24 below zero) Item 29 is Item 24, penalties left out
    o["29"] = o["24"] if o["24"] < 0 else o["24"] + o["28"]
    return o


def _has_spouse(data: dict) -> bool:
    return any(inc.s(data.get(k)) for k in ("spouseName", "spouseTin", "i36B", "i47B", "spouseTaxRate"))


def compute(data: dict, ctx: Context) -> list[dict]:
    kind = inc.kinds(data)
    atc = "".join(inc.s(data.get("atc")).split()).upper()
    # eBIRForms sets the rate from the ATC (II015 and II017 are 8%); without one the typed rate stands
    rate = ("eight" if atc in ("II015", "II017") else "graduated") if atc else (inc.s(data.get("taxRate")) or "graduated")
    sides = {"A": _side(data, "A", ctx.period.year, rate), "B": _side(data, "B", ctx.period.year, inc.s(data.get("spouseTaxRate")) or rate)}
    spouse = _has_spouse(data)
    out = []
    for i in ORDER:
        for s in SIDES:
            if s == "B" and not spouse:
                continue
            label = TYPED.get(i) or DERIVED[i]
            out.append(inc.line(f"{i}{s}", f"{label} ({'taxpayer' if s == 'A' else 'spouse'})", sides[s][i], kind(f"i{i}{s}") if i in TYPED else "derived"))
    i30 = sides["A"]["29"] + (sides["B"]["29"] if spouse else ZERO)
    out.append(inc.line("30", "Aggregate Amount Payable/(Overpayment)", i30, "derived"))
    out.append(inc.hidden("_c", {"A": sides["A"], "B": sides["B"], "i30": i30, "rate": rate}))
    return out


def needs(data: dict, ctx: Context) -> list[Need]:
    c = inc.payload(compute(data, ctx))
    return inc.common_needs(data, ctx, "1701A", c["A"]["22"] < 0)


def export_rows(data: dict, comp: list[dict], ctx: Context) -> tuple[list[tuple[str, str]], str]:
    c = ctx.company
    cp = inc.payload(comp)
    A, B, rate = cp["A"], cp["B"], cp["rate"]
    spouse = _has_spouse(data)
    t = inc.tin(c)
    p = ctx.period
    mm = f"{p.end.month:02d}"
    atc = inc.chosen_atc(data.get("atc"), "1701A")
    ttype = inc.taxpayer_type(c)
    civil = inc.civil_status(c)
    married = civil == "married"
    r = inc.Rows(NS)
    r.p("txtMonth", mm)
    r.p("txtYear", str(p.year))
    r.b("optAmendedReturn_1", ctx.is_amended)
    r.b("optAmendedReturn_2", not ctx.is_amended)
    short = inc.s(data.get("shortPeriod")) == "yes"
    r.b("optShortPeriod_1", short)
    r.b("optShortPeriod_2", not short)
    r.p("txtTIN1", t["t1"])
    r.p("txtTIN2", t["t2"])
    r.p("txtTIN3", t["t3"])
    r.p("txtBranchCode", t["branch3"])
    r.p("txtRDOCode", c.get("ph_rdo") or "")
    r.b("optTaxType_1", ttype == "single")
    r.b("optTaxType_2", ttype == "prof")
    for n, code in enumerate(inc.ATC["1701A"], start=1):
        r.b(f"optATC_{n}", atc == code)
    r.enc("txtTaxpayerName", inc.name_given(c))
    r.enc("txtAddress", inc.address(c))
    r.p("txtZipCode", c.get("ph_zip") or "")
    r.p("txtBirthDate", dob(c.get("ph_birthdate")))
    r.g("txtEmail", c.get("ph_email") or "")
    r.p("txtCitizenship", c.get("ph_citizenship") or "")
    fc = inc.s(data.get("foreignCredit")) == "yes"
    r.b("optForeignTaxCredits_1", fc)
    r.b("optForeignTaxCredits_2", not fc)
    r.enc("txtForeignTaxNumber", data.get("foreignTaxNo"))
    r.p("txtTelNum", ctx.contact_number or c.get("ph_contact_number") or "")
    r.b("optCivilStatus_1", civil == "single")
    r.b("optCivilStatus_2", married)
    r.b("optCivilStatus_3", civil == "separated")
    r.b("optCivilStatus_4", civil == "widow")
    r.b("optSpouseIncome_1", married and inc.s(data.get("spouseIncome")) == "yes")
    r.b("optSpouseIncome_2", married and inc.s(data.get("spouseIncome")) == "no")
    r.b("optFilingStatus_1", married and inc.s(data.get("filing")) == "joint")
    r.b("optFilingStatus_2", married and inc.s(data.get("filing")) == "separate")
    r.b("optTaxRate_1", rate != "eight")
    r.b("optTaxRate_2", rate == "eight")
    for i in range(20, 30):
        r.a(f"txt{i}A", A[str(i)])
        r.a(f"txt{i}B", B[str(i)] if spouse else 0)
    r.a("txt30", cp["i30"])
    over = inc.s(data.get("over"))
    r.b("optRefund_1", over == "refund")
    r.b("optRefund_2", over == "tcc")
    r.b("optRefund_3", over == "carry")
    r.p("txtNumberAttachments", inc.s(data.get("attachments")) or "0")
    inc.payments(r, data)
    r.p("txtPg2TIN1", t["t1"])
    r.p("txtPg2TIN2", t["t2"])
    r.p("txtPg2TIN3", t["t3"])
    r.p("txtPg2BranchCode", t["branch3"])
    r.p("txtPg2TaxpayerName", inc.name_raw(c))
    desc = {41: "i41label", 42: "i42label", 50: "i50label", 51: "i51label", 63: "i63label"}
    for i in range(36, 66):
        if i in desc:
            r.enc(f"txt{i}Desc", data.get(desc[i]))
        r.a(f"txt{i}A", A[str(i)])
        r.a(f"txt{i}B", B[str(i)] if spouse else 0)
    stin = inc.spouse_tin(data)
    r.p("txtSpouseTIN1", stin[0:3])
    r.p("txtSpouseTIN2", stin[3:6])
    r.p("txtSpouseTIN3", stin[6:9])
    r.p("txtSpouseBranchCode", "")
    r.p("txtSpouseRDOCode", inc.s(data.get("spouseRdo")) or "000")
    st = inc.s(data.get("spouseType"))
    r.b("optSpouseTaxType_1", st == "single")
    r.b("optSpouseTaxType_2", st == "prof")
    satc = inc.s(data.get("spouseAtc")).upper()
    for n, code in enumerate(inc.ATC["1701A"], start=1):
        r.b(f"optSpouseATC_{n}", satc == code)
    r.enc("txtSpouseName", data.get("spouseName"))
    r.enc("txtSpouseTelNum", data.get("spouseContact"))
    r.enc("txtSpouseCitizenship", data.get("spouseCitizenship"))
    sfc = inc.s(data.get("spouseForeignCredit"))
    r.b("optSpouseFTC_1", sfc == "yes")
    r.b("optSpouseFTC_2", sfc == "no")
    r.enc("txtSpouseFTN", data.get("spouseForeignTaxNo"))
    srate = inc.s(data.get("spouseTaxRate"))
    r.b("optSpouseTaxRate_1", srate == "graduated")
    r.b("optSpouseTaxRate_2", srate == "eight")
    r.p("txtCurrentPage", "1")
    r.p("txtMaxPage", "2")
    r.enc("txtLineBus", inc.s(data.get("lineBus")) or c.get("ph_line_of_business"))
    r.p("txtCtrmodalPartIVA", "0")
    r.p("txtCtrmodalPartIVB", "0")
    for k in ("txtZIP", "txtEnabledInputsOnValidation", "txtDisabledInputs", "txtEnabledLinks", "txtIsSpouseDisabled"):
        r.e(k)
    r.p("txtIsTaxFilerDisabled", "false")
    for k in ("txtAttachmentTypes", "txtTIN4", "txtDisabledOnSave", "txtEnabledOnSave"):
        r.e(k)
    r.p("txtVersion", "11112018")
    r.e("txtdisabledID")
    for k in ("txtmodalPartIVA_C1", "txtmodalPartIVA_C2", "txtmodalPartIVB_C1", "txtmodalPartIVB_C2"):
        r.p(k, "0.00")
    r.g("driveSelectTPExport", "0")
    inc.trailer(r, ctx.final, "N")
    name = f"{t['t1']}{t['t2']}{t['t3']}{t['branch3']}1701A{mm}{p.year}.xml"
    return r.out, name


def write_export(rows: list[tuple[str, str]]) -> str:
    return inc.write_1701a(rows)


def key_figures(comp: list[dict]) -> dict[str, Decimal]:
    c = inc.payload(comp)
    return {"tax_due": c["A"]["20"], "credits": c["A"]["21"], "payable": c["i30"]}
