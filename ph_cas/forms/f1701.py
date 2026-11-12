"""BIR Form 1701, Annual Income Tax Return for Individuals (including Mixed Income
Earner), Estates and Trusts (January 2018 ENCS). Exported for eBIRForms (four
pages, 837 fields) and printed on the blank. Whole pesos.

Two columns, A (taxpayer) and B (spouse); per-column keys end in A or B.
Books (column A, the year from the tax engine): sales, cogs, deduct (itemized
total, when Schedule 4 has no lines), nolco4D (NOLCO applied), prevPaid (tax
payments for the first three quarters), cwt (creditable tax withheld per 2307),
rate and method from the Company.
Typed: comp (taxable compensation) and compCwt, returns, other (non-operating
income), Schedule 4 lines s4_1 to s4_17d, Schedule 5 s5_1 to s5_6 amounts,
specialRate, shareGovt, excess, install, interest, surcharge, compromise, Part
IX reconciliation ix1 to ix9 with descriptions, atc, over, attachments, spouse
block. Derived: the rest.
"""

from decimal import Decimal

from ph_cas.forms import income as inc
from ph_cas.forms.engine import Context
from ph_cas.forms.export import dob
from ph_cas.forms.money import ZERO
from ph_cas.forms.needs import Need

NS = "frm1701:"
SIDES = ("A", "B")
S4 = [str(i) for i in range(1, 17)] + ["17a", "17b", "17c", "17d"]
S4_LABELS = ["Amortizations", "Bad debts", "Charitable contributions", "Depletion", "Depreciation", "Entertainment, amusement and recreation", "Fringe benefits", "Interest", "Losses", "Pension trusts", "Rental", "Research and development", "Salaries, wages and allowances", "SSS, GSIS, Philhealth, HDMF and other contributions", "Taxes and licenses", "Transportation and travel", "Janitorial and messengerial services", "Professional fees", "Security services", "Others (specify)"]


def _side_inputs(side: str) -> list:
    who = "" if side == "A" else " (spouse)"
    base = [
        (f"rate{side}", f"Tax rate{who}", "select:graduated,eight"),
        (f"method{side}", f"Method of deduction{who}", "select:osd,itemized"),
        (f"comp{side}", f"Taxable compensation income{who}", "money"),
        (f"compCwt{side}", f"Tax withheld on compensation (2316){who}", "money"),
        (f"sales{side}", f"Sch 3.8 Sales/revenues/receipts/fees{who}", "money"),
        (f"returns{side}", f"Sch 3.9 Sales returns, allowances and discounts{who}", "money"),
        (f"cogs{side}", f"Sch 3.11 Cost of sales or services{who}", "money"),
        (f"deduct{side}", f"Sch 3.13 Ordinary allowable itemized deductions (if Schedule 4 is blank){who}", "money"),
        (f"other{side}", f"Sch 3.19 Non-operating income{who}", "money"),
        (f"specialRate{side}", f"Part VI.2 Tax due on income under special rate{who}", "money"),
        (f"shareGovt{side}", f"Part VI.3 Less: share of other government agencies{who}", "money"),
        (f"excess{side}", f"Part VII.1 Prior year's excess credits{who}", "money"),
        (f"prevPaid{side}", f"Part VII.2 Tax payments for the first three quarters{who}", "money"),
        (f"cwt{side}", f"Part VII creditable tax withheld per 2307{who}", "money"),
        (f"install{side}", f"25 Portion allowed for second installment{who}", "money"),
        (f"interest{side}", f"27 Interest{who}", "money"),
        (f"surcharge{side}", f"28 Surcharge{who}", "money"),
        (f"compromise{side}", f"29 Compromise{who}", "money"),
    ]
    base += [(f"s4_{k}{side}", f"Sch 4.{k} {label}{who}", "money") for k, label in zip(S4, S4_LABELS)]
    base += [(f"ix{n}{side}", f"Part IX.{n} {'add' if n <= 4 else 'less'} reconciling item{who}", "money") for n in (1, 2, 3, 4, 6, 7, 8, 9)]
    return base


INPUTS = (
    [
        ("atc", "7 ATC", "select:II012,II014,II013,II011,II015,II017,II016"),
        ("over", "Overpayment: refund, TCC or carry over", "select:refund,tcc,carry"),
        ("attachments", "33 Number of attachments", "text"),
        ("shortPeriod", "3 Short period return", "select:no,yes"),
        ("spouseIncome", "17 Spouse has income (married)", "select:yes,no"),
        ("filing", "18 Filing status (married)", "select:joint,separate"),
        ("incomeExempt", "19 Income subject to exemption", "select:no,yes"),
        ("incomeSpecial", "20 Income subject to special rate", "select:no,yes"),
        ("foreignCredit", "13 Claiming foreign tax credits", "select:no,yes"),
        ("foreignTaxNo", "14 Foreign tax number", "text"),
        ("lineBus", "Line of business (blank: the Company's)", "text"),
        ("spouseIncomeExempt", "Spouse: income subject to exemption", "select:no,yes"),
        ("spouseIncomeSpecial", "Spouse: income subject to special rate", "select:no,yes"),
        ("s5_1amt", "Sch 5.1 Special allowable deduction (taxpayer)", "money"),
        ("s5_2amt", "Sch 5.2 Special allowable deduction (taxpayer)", "money"),
        ("s5_4amt", "Sch 5.4 Special allowable deduction (spouse)", "money"),
        ("s5_5amt", "Sch 5.5 Special allowable deduction (spouse)", "money"),
        ("nolco4D", "Sch 6 NOLCO applied this year (taxpayer)", "money"),
        ("nolco9D", "Sch 6 NOLCO applied this year (spouse)", "money"),
    ]
    + [(f"ix{n}descA", f"Part IX.{n} description", "text") for n in (2, 3, 4, 6, 7, 8, 9)]
    + _side_inputs("A")
    + _side_inputs("B")
    + inc.SPOUSE_INPUTS
)


def feed(ctx: Context) -> dict:
    company = ctx.company["name"]
    c = ctx.company
    p = ctx.period
    a = inc.annual(company, p.start, p.end)
    eight = (c.get("ph_income_tax_option") or "") == "8% option (individual)"
    osd = (c.get("ph_deduction_method") or "Itemized") != "Itemized"
    figures = {
        "rateA": "eight" if eight else "graduated",
        "methodA": "osd" if osd else "itemized",
        "salesA": inc.peso_text(inc.nonneg_peso(a.get("Sales"))),
        "cogsA": inc.peso_text(inc.nonneg_peso(a.get("COGS"))),
        "prevPaidA": inc.peso_text(a.get("Prior quarters", ZERO)),
        "cwtA": inc.peso_text(a.get("Credits 2307", ZERO)),
    }
    if not osd and not eight:
        figures["deductA"] = inc.peso_text(inc.nonneg_peso(a.get("Deductions")))
        figures["nolco4D"] = inc.peso_text(inc.nonneg_peso(a.get("NOLCO")))
    lines = [
        inc.books_line("salesA", "Schedule 3 Item 8, sales/revenues/receipts/fees for the year", figures["salesA"], company, p.start, p.end),
        inc.books_line("cogsA", "Schedule 3 Item 11, cost of sales or services", figures["cogsA"], company, p.start, p.end, "purchase-invoice"),
        inc.books_line("prevPaidA", "Part VII Item 2, tax payments for the first three quarters (filed 1701Q returns)", figures["prevPaidA"], company, p.start, p.end, "ph-tax-return"),
        inc.books_line("cwtA", "Part VII, creditable tax withheld per 2307 for the year", figures["cwtA"], company, p.start, p.end, "ph-2307-received"),
    ]
    if "deductA" in figures:
        lines.append(inc.books_line("deductA", "Schedule 3 Item 13, ordinary allowable itemized deductions", figures["deductA"], company, p.start, p.end, "purchase-invoice"))
    warnings = [f"Schedule 3 Item {i} is below zero in the books; it is shown as 0." for i, v in (("8", a.get("Sales", ZERO)), ("11", a.get("COGS", ZERO))) if v < 0]
    return {"figures": figures, "lines": lines, "warnings": warnings}


def _side(data: dict, s: str, year: int) -> dict:
    w = lambda k: inc.w(data, k + s)  # noqa: E731
    o: dict = {}
    o["comp"] = w("comp")
    o["sales"], o["returns"] = w("sales"), w("returns")
    o["netSales"] = o["sales"] - o["returns"]
    o["cogs"] = w("cogs")
    o["gross"] = o["netSales"] - o["cogs"]
    o["method"] = inc.s(data.get("method" + s)) or "osd"
    sched4 = sum((inc.w(data, f"s4_{k}{s}") for k in S4), ZERO)
    special = (inc.w(data, "s5_1amt") + inc.w(data, "s5_2amt")) if s == "A" else (inc.w(data, "s5_4amt") + inc.w(data, "s5_5amt"))
    nolco_rows = (4, 5, 6, 7) if s == "A" else (9, 10, 11, 12)
    itemized = o["method"] != "osd"
    o["nolco"] = sum((inc.w(data, f"nolco{r}D") for r in nolco_rows), ZERO) if itemized else ZERO
    o["sched4"] = sched4
    o["itemizedOrdinary"] = sched4 if sched4 > 0 else w("deduct")
    o["itemizedSpecial"] = special
    o["deductions"] = inc.whole_peso(o["netSales"] * Decimal("0.4")) if not itemized else o["itemizedOrdinary"] + o["itemizedSpecial"] + o["nolco"]
    o["netBiz"] = o["gross"] - o["deductions"]
    o["otherInc"] = w("other")
    o["netBizTotal"] = o["netBiz"] + o["otherInc"]
    o["rate"] = inc.s(data.get("rate" + s)) or "graduated"
    eight = o["rate"] == "eight"
    o["gross8"] = o["netSales"] + o["otherInc"]
    o["taxable8"] = max(ZERO, o["gross8"] - (inc.REDUCTION if s == "A" else ZERO))
    o["tax8biz"] = inc.whole_peso(o["taxable8"] * inc.EIGHT)
    o["taxableTotal"] = o["comp"] + (o["taxable8"] if eight else o["netBizTotal"])
    o["compTaxFlat"] = inc.graduated_tax(o["comp"], year) if eight else ZERO
    o["taxDueRegular"] = (o["compTaxFlat"] + o["tax8biz"]) if eight else inc.graduated_tax(o["comp"] + o["netBizTotal"], year)
    o["specialRate"], o["shareOtherGovt"] = w("specialRate"), w("shareGovt")
    o["netSpecial"] = o["specialRate"] - o["shareOtherGovt"]
    o["taxDue"] = o["taxDueRegular"] + o["netSpecial"]
    o["prevPaid"], o["cwt"], o["excess"], o["taxWithheldComp"] = w("prevPaid"), w("cwt"), w("excess"), w("compCwt")
    o["credits"] = o["prevPaid"] + o["cwt"] + o["excess"] + o["taxWithheldComp"]
    o["payable"] = o["taxDue"] - o["credits"]
    o["installment"] = w("install")
    o["afterInstall"] = o["payable"] - o["installment"]
    o["interest"], o["surcharge"], o["compromise"] = w("interest"), w("surcharge"), w("compromise")
    o["penalties"] = o["interest"] + o["surcharge"] + o["compromise"]
    o["totalPayable"] = o["afterInstall"] + o["penalties"]
    o["ixTotalAdd"] = sum((w(f"ix{n}") for n in (1, 2, 3, 4)), ZERO)
    o["ixTotalLess"] = sum((w(f"ix{n}") for n in (6, 7, 8, 9)), ZERO)
    o["ixNetTaxable"] = o["ixTotalAdd"] - o["ixTotalLess"]
    return o


LABELS = [
    ("comp", "Sch 1", "Taxable Compensation Income", "comp"), ("taxWithheldComp", "Sch 1", "Tax Withheld on Compensation", "compCwt"), ("sales", "Sch 3.8", "Sales/Revenues/Receipts/Fees", "sales"), ("returns", "Sch 3.9", "Less: Sales Returns, Allowances and Discounts", "returns"),
    ("netSales", "Sch 3.10", "Net Sales/Revenues/Receipts/Fees", None), ("cogs", "Sch 3.11", "Less: Cost of Sales/Services", "cogs"), ("gross", "Sch 3.12", "Gross Income/(Loss) from Operation", None),
    ("itemizedOrdinary", "Sch 3.13", "Ordinary Allowable Itemized Deductions", "deduct"), ("itemizedSpecial", "Sch 3.14", "Special Allowable Itemized Deductions", None), ("nolco", "Sch 3.15", "NOLCO", None),
    ("deductions", "Sch 3.16/17", "Total Allowable Deductions (itemized, or OSD 40% of net sales)", None), ("netBiz", "Sch 3.18", "Net Income/(Loss) from Business or Profession", None), ("otherInc", "Sch 3.19", "Non-operating Income", "other"),
    ("netBizTotal", "Sch 3.23", "Total Taxable Income from Business or Profession", None), ("taxableTotal", "Sch 3.24", "Total Taxable Income (compensation and business)", None), ("taxable8", "Sch 3.30", "Taxable Income under the 8% Option", None),
    ("taxDueRegular", "Part VI.1", "Tax Due under the Regular or 8% Rate", None), ("specialRate", "Part VI.2", "Tax Due on Income under Special Rate", "specialRate"), ("shareOtherGovt", "Part VI.3", "Less: Share of Other Government Agencies", "shareGovt"),
    ("taxDue", "22", "Total Income Tax Due", None), ("excess", "Part VII.1", "Prior Year's Excess Credits", "excess"), ("prevPaid", "Part VII.2", "Tax Payments for the First Three Quarters", "prevPaid"), ("cwt", "Part VII", "Creditable Tax Withheld per BIR Form 2307", "cwt"),
    ("credits", "23", "Less: Total Tax Credits/Payments", None), ("payable", "24", "Net Tax Payable/(Overpayment)", None), ("installment", "25", "Less: Portion Allowed for Second Installment", "install"), ("afterInstall", "26", "Amount Still Payable/(Overpayment)", None),
    ("interest", "27", "Interest", "interest"), ("surcharge", "28", "Surcharge", "surcharge"), ("compromise", "29", "Compromise", "compromise"), ("penalties", "30", "Total Penalties", None), ("totalPayable", "31", "Total Amount Payable/(Overpayment)", None),
]


def _has_spouse(data: dict) -> bool:
    return any(inc.s(data.get(k)) for k in ("rateB", "methodB", "spouseName", "spouseTin", "salesB", "compB"))


def compute(data: dict, ctx: Context) -> list[dict]:
    kind = inc.kinds(data)
    year = ctx.period.year
    sides = {s: _side(data, s, year) for s in SIDES}
    spouse = _has_spouse(data)
    out = []
    for key, item, label, typed in LABELS:
        for s in SIDES:
            if s == "B" and not spouse:
                continue
            o = sides[s]
            k = "derived" if typed is None or (key == "itemizedOrdinary" and o["sched4"] > 0) else kind(typed + s)
            out.append(inc.line(f"{item}{s}", f"{label} ({'taxpayer' if s == 'A' else 'spouse'})", o[key], k))
    aggregate = sides["A"]["totalPayable"] + (sides["B"]["totalPayable"] if spouse else ZERO)
    out.append(inc.line("32", "Aggregate Amount Payable/(Overpayment)", aggregate, "derived"))
    out.append(inc.hidden("_c", {"A": sides["A"], "B": sides["B"], "aggregate": aggregate}))
    return out


def needs(data: dict, ctx: Context) -> list[Need]:
    c = inc.payload(compute(data, ctx))
    return inc.common_needs(data, ctx, "1701", c["A"]["payable"] < 0)


def export_rows(data: dict, comp: list[dict], ctx: Context) -> tuple[list[tuple[str, str]], str]:
    c = ctx.company
    cp = inc.payload(comp)
    A, B = cp["A"], cp["B"]
    spouse = _has_spouse(data)
    t = inc.tin(c)
    p = ctx.period
    mm = f"{p.end.month:02d}"
    atc = inc.chosen_atc(data.get("atc"), "1701")
    ttype = inc.taxpayer_type(c)
    civil = inc.civil_status(c)
    married = civil == "married"
    rate, method = A["rate"], A["method"]
    r = inc.Rows(NS)
    yn = lambda k: inc.s(data.get(k)) == "yes"  # noqa: E731
    r.p("txtPg1I1Month", mm)
    r.p("txtPg1I1Year", str(p.year))
    r.b("rdoPg1I2AmendedYes", ctx.is_amended)
    r.b("rdoPg1I2AmendedNo", not ctx.is_amended)
    r.b("rdoPg1I3ShortPeriodYes", yn("shortPeriod"))
    r.b("rdoPg1I3ShortPeriodNo", not yn("shortPeriod"))
    r.p("txtPg1I4TIN1", t["t1"])
    r.p("txtPg1I4TIN2", t["t2"])
    r.p("txtPg1I4TIN3", t["t3"])
    r.p("txtPg1I4BranchCode", t["branch3"])
    r.p("txtPg1I5RDOCode", c.get("ph_rdo") or "")
    r.b("rdoPg1I6TaxpayerTypeS", ttype == "single")
    r.b("rdoPg1I6TaxpayerTypeP", ttype == "prof")
    r.b("rdoPg1I6TaxpayerTypeE", False)
    r.b("rdoPg1I6TaxpayerTypeT", False)
    r.b("rdoPg1I6TaxpayerTypeC", False)
    for code in inc.ATC["1701"]:
        r.b(f"rdoPg1I7ATC_{code}", atc == code)
    r.enc("txtPg1I8TaxpayerName", inc.name_given(c))
    r.enc("txtPg1I9Address", inc.address(c))
    r.p("txtPg1I9AZipCode", c.get("ph_zip") or "")
    r.p("txtPg1I10BirthDate", dob(c.get("ph_birthdate")))
    r.g("txtEmail", c.get("ph_email") or "")
    r.p("txtPg1I12Citizenship", c.get("ph_citizenship") or "")
    r.b("rdoPg1I13ForeignTaxCreditsYes", yn("foreignCredit"))
    r.b("rdoPg1I13ForeignTaxCreditsNo", not yn("foreignCredit"))
    r.enc("txtPg1I14ForeignTaxNumber", data.get("foreignTaxNo"))
    r.p("txtPg1I15TelNum", ctx.contact_number or c.get("ph_contact_number") or "")
    r.b("rdoPg1I16CivilStatusS", civil == "single")
    r.b("rdoPg1I16CivilStatusM", married)
    r.b("rdoPg1I16CivilStatusLS", civil == "separated")
    r.b("rdoPg1I16CivilStatusW", civil == "widow")
    r.b("rdoPg1I17SpouseIncomeYes", married and inc.s(data.get("spouseIncome")) == "yes")
    r.b("rdoPg1I17SpouseIncomeNo", married and inc.s(data.get("spouseIncome")) == "no")
    r.b("rdoPg1I18FilingStatusJ", married and inc.s(data.get("filing")) == "joint")
    r.b("rdoPg1I18FilingStatusS", married and inc.s(data.get("filing")) == "separate")
    r.b("rdoPg1I19IncomeExemptYes", yn("incomeExempt"))
    r.b("rdoPg1I19IncomeExemptNo", not yn("incomeExempt"))
    r.b("rdoPg1I20IncomeSpecialYes", yn("incomeSpecial"))
    r.b("rdoPg1I20IncomeSpecialNo", not yn("incomeSpecial"))
    r.b("rdoPg1I21TaxRateG", rate != "eight")
    r.b("rdoPg1I21AMethodDeductionI", rate != "eight" and method == "itemized")
    r.b("rdoPg1I21AMethodDeductionO", rate != "eight" and method != "itemized")
    r.b("rdoPg1I21TaxRateP", rate == "eight")
    bv = lambda key: B[key] if spouse else ZERO  # noqa: E731
    r.a("txtPg1I22ATaxDue", A["taxDue"])
    r.a("txtPg1I22BTaxDue", bv("taxDue"))
    r.a("txtPg1I23A", A["credits"])
    r.a("txtPg1I23B", bv("credits"))
    r.a("txtPg1I24ATaxPayable", A["payable"])
    r.a("txtPg1I24BTaxPayable", bv("payable"))
    r.a("txtPg1I25A", A["installment"])
    r.a("txtPg1I25B", bv("installment"))
    r.a("txtPg1I26A", A["afterInstall"])
    r.a("txtPg1I26B", bv("afterInstall"))
    r.a("txtPg1I27A", A["interest"])
    r.a("txtPg1I27B", bv("interest"))
    r.a("txtPg1I28A", A["surcharge"])
    r.a("txtPg1I28B", bv("surcharge"))
    r.a("txtPg1I29A", A["compromise"])
    r.a("txtPg1I29B", bv("compromise"))
    r.a("txtPg1I30A", A["penalties"])
    r.a("txtPg1I30B", bv("penalties"))
    r.a("txtPg1I31ATotalAmtPyble", A["totalPayable"])
    r.a("txtPg1I31BTotalAmtPyble", bv("totalPayable"))
    r.a("txtPg1I32AggregateAmtPyble", cp["aggregate"])
    over = inc.s(data.get("over"))
    r.b("rdoPg1OverpaymentRefund", over == "refund")
    r.b("rdoPg1OverpaymentTCC", over == "tcc")
    r.b("rdoPg1OverpaymentCarryOver", over == "carry")
    digits = "".join(ch for ch in inc.s(data.get("attachments")) if ch.isdigit()) or "0"
    r.p("txtPg1I33NumberOfAttachments", digits.rjust(2, "0")[-2:])
    for k in ("txtPg1I34Agency", "txtPg1I34Number", "txtPg1I34Date", "txtPg1I34Amount", "txtPg1I35Agency", "txtPg1I235Number", "txtPg1I35Date", "txtPg1I35Amount", "txtPg1I36Number", "txtPg1I36Date", "txtPg1I36Amount", "txtPg1I37Particular", "txtPg1I37Agency", "txtPg1I37Number", "txtPg1I37Date", "txtPg1I37Amount"):
        r.e(k)
    raw = inc.name_raw(c)
    r.p("txtPg2TIN1", t["t1"])
    r.p("txtPg2TIN2", t["t2"])
    r.p("txtPg2TIN3", t["t3"])
    r.p("txtPg2BranchCode", t["branch3"])
    r.p("txtPg2TaxpayerName", raw)
    stin = inc.spouse_tin(data)
    r.p("txtPg2I1TIN1", stin[0:3])
    r.p("txtPg2I1TIN2", stin[3:6])
    r.p("txtPg2I1TIN3", stin[6:9])
    r.e("txtPg2I1BranchCode")
    r.p("txtPg2I2SpouseRDOCode", inc.s(data.get("spouseRdo")) or "000")
    st = inc.s(data.get("spouseType"))
    r.b("rdoPg2I3SpouseTypeS", st == "single")
    r.b("rdoPg2I3SpouseTypeP", st in ("prof", "biz"))
    r.b("rdoPg2I3SpouseTypeC", st == "comp")
    satc = inc.s(data.get("spouseAtc")).upper()
    for code in inc.ATC["1701"]:
        r.b(f"rdoPg2I4ATC_{code}", satc == code)
    r.enc("txtPg2I5SpouseName", data.get("spouseName"))
    r.enc("txtPg2I6TelNum", data.get("spouseContact"))
    r.enc("txtPg2I7Citizenship", data.get("spouseCitizenship"))
    sfc = inc.s(data.get("spouseForeignCredit"))
    r.b("rdoPg2I8ForeignTaxCreditsYes", sfc == "yes")
    r.b("rdoPg2I8ForeignTaxCreditsNo", sfc == "no")
    r.enc("txtPg2I9ForeignTaxNumber", data.get("spouseForeignTaxNo"))
    sie, sis = inc.s(data.get("spouseIncomeExempt")), inc.s(data.get("spouseIncomeSpecial"))
    r.b("rdoPg2I10IncomeExemptYes", sie == "yes")
    r.b("rdoPg2I10IncomeExemptNo", sie == "no")
    r.b("rdoPg2I11IncomeSpecialYes", sis == "yes")
    r.b("rdoPg2I11IncomeSpecialNo", sis == "no")
    srate = inc.s(data.get("rateB")) if spouse else ""
    smethod = inc.s(data.get("methodB")) or "osd"
    r.b("rdoPg2I12TaxRateG", srate == "graduated")
    r.b("rdoPg2I12AMethodDeductionI", srate not in ("eight", "") and smethod == "itemized")
    r.b("rdoPg2I12AMethodDeductionO", srate not in ("eight", "") and smethod != "itemized")
    r.b("rdoPg2I12TaxRateP", srate == "eight")
    r.b("chkPg2IShed1a_1Taxpayer", A["comp"] > 0)
    r.e("txtPg2IShed1a_1TPName")
    r.b("chkPg2IShed1a_1Spouse", False)
    for k in ("txtPg2IShed1a_1SName", "txtPg2IShed1a_TIN1", "txtPg2IShed1a_TIN2", "txtPg2IShed1a_TIN3", "txtPg2IShed1a_BranchCode"):
        r.e(k)
    r.b("chkPg2IShed2a_2Taxpayer", False)
    r.e("txtPg2IShed2a_2TPName")
    r.b("chkPg2IShed2a_2Spouse", spouse and B["comp"] > 0)
    for k in ("txtPg2IShed2a_2SName", "txtPg2IShed2a_TIN1", "txtPg2IShed2a_TIN2", "txtPg2IShed2a_TIN3", "txtPg2IShed2a_BranchCode"):
        r.e(k)
    r.a("txtPg2IShed1c_1CI", A["comp"])
    r.a("txtPg2IShed1c_1TW", A["taxWithheldComp"])
    r.a("txtPg2IShed1c_2CI", bv("comp"))
    r.a("txtPg2IShed1c_2TW", bv("taxWithheldComp"))
    r.a("txtPg2IShed1c_3ACI", A["comp"])
    r.a("txtPg2IShed1c_3ATW", A["taxWithheldComp"])
    r.a("txtPg2IShed1c_3BCI", bv("comp"))
    r.a("txtPg2IShed1c_3BTW", bv("taxWithheldComp"))
    for s, o in (("A", A), ("B", B)):
        on = s == "A" or spouse
        r.a(f"txtPg2IShed2_4{s}", o["comp"] if on else 0)
        r.z(f"txtPg2IShed2_5{s}")
        r.a(f"txtPg2IShed2_6{s}", o["comp"] if on else 0)
        r.a(f"txtPg2IShed2_7{s}", o["compTaxFlat"] if on else 0)
    grad = lambda o: o["rate"] != "eight"  # noqa: E731
    itm = lambda o: o["method"] != "osd"  # noqa: E731
    s3a = {
        8: lambda o: o["sales"], 9: lambda o: o["returns"], 10: lambda o: o["netSales"], 11: lambda o: o["cogs"], 12: lambda o: o["gross"],
        13: lambda o: o["itemizedOrdinary"] if itm(o) else ZERO, 14: lambda o: o["itemizedSpecial"] if itm(o) else ZERO, 15: lambda o: o["nolco"] if itm(o) else ZERO,
        16: lambda o: o["deductions"] if itm(o) else ZERO, 17: lambda o: ZERO if itm(o) else o["deductions"], 18: lambda o: o["netBiz"], 19: lambda o: o["otherInc"],
        20: lambda o: ZERO, 21: lambda o: ZERO, 22: lambda o: o["otherInc"], 23: lambda o: o["netBizTotal"], 24: lambda o: o["taxableTotal"], 25: lambda o: o["taxDueRegular"],
    }
    for i in range(8, 26):
        if i in (19, 20):
            r.e(f"txtPg2IShed3_{i}Desc")
        r.a(f"txtPg2IShed3_{i}A", s3a[i](A) if grad(A) else 0)
        r.a(f"txtPg2IShed3_{i}B", s3a[i](B) if spouse and grad(B) else 0)
    r.p("txtPg3TIN1", t["t1"])
    r.p("txtPg3TIN2", t["t2"])
    r.p("txtPg3TIN3", t["t3"])
    r.p("txtPg3BranchCode", t["branch3"])
    r.p("txtPg3TaxpayerName", raw)
    s3b = {26: lambda o: o["netSales"], 27: lambda o: o["otherInc"], 28: lambda o: o["gross8"], 29: lambda o: o["gross8"] - o["taxable8"], 30: lambda o: o["taxable8"], 31: lambda o: o["tax8biz"], 32: lambda o: o["taxDueRegular"]}
    for i in range(26, 33):
        if i == 27:
            r.e(f"txtPg3IShed3_{i}Desc")
        r.a(f"txtPg3IShed3_{i}A", s3b[i](A) if not grad(A) else 0)
        r.a(f"txtPg3IShed3_{i}B", s3b[i](B) if spouse and not grad(B) else 0)
    s4line = lambda k, s, o: inc.w(data, f"s4_{k}{s}") if itm(o) and (s == "A" or spouse) else ZERO  # noqa: E731
    for i in range(1, 17):
        r.a(f"txtPg3IShed4_{i}A", s4line(str(i), "A", A))
        r.a(f"txtPg3IShed4_{i}B", s4line(str(i), "B", B))
    for x in ("a", "b", "c"):
        r.a(f"txtPg3IShed4_17{x}A", s4line(f"17{x}", "A", A))
        r.a(f"txtPg3IShed4_17{x}B", s4line(f"17{x}", "B", B))
    r.e("txtPg3IShed4_17dDesc")
    r.a("txtPg3IShed4_17dA", s4line("17d", "A", A))
    r.a("txtPg3IShed4_17dB", s4line("17d", "B", B))
    r.a("txtPg3IShed4_18A", A["itemizedOrdinary"] if itm(A) else 0)
    r.a("txtPg3IShed4_18B", B["itemizedOrdinary"] if spouse and itm(B) else 0)
    for i in (1, 2):
        r.e(f"txtPg3IShed5_{i}Desc")
        r.e(f"txtPg3IShed5_{i}Legal")
        r.a(f"txtPg3IShed5_{i}Amt", inc.w(data, f"s5_{i}amt") if itm(A) else 0)
    r.a("txtPg3IShed5_3", A["itemizedSpecial"] if itm(A) else 0)
    for i in (4, 5):
        r.e(f"txtPg3IShed5_{i}Desc")
        r.e(f"txtPg3IShed5_{i}Legal")
        r.a(f"txtPg3IShed5_{i}Amt", inc.w(data, f"s5_{i}amt") if spouse and itm(B) else 0)
    r.a("txtPg3IShed5_6", B["itemizedSpecial"] if spouse and itm(B) else 0)
    for i in (1, 2, 3):
        r.z(f"txtPg3IShed6_{i}A")
        r.z(f"txtPg3IShed6_{i}B")
    for i in (4, 5, 6, 7):
        r.e(f"txtPg3IShed6_{i}Year")
        for col in "ABCDE":
            r.z(f"txtPg3IShed6_{i}{col}")
    r.a("txtPg3IShed6_8D", A["nolco"])
    r.p("txtPg4TIN1", t["t1"])
    r.p("txtPg4TIN2", t["t2"])
    r.p("txtPg4TIN3", t["t3"])
    r.p("txtPg4BranchCode", t["branch3"])
    r.p("txtPg4TaxpayerName", raw)
    for i in (9, 10, 11, 12):
        r.e(f"txtPg4IShed6_{i}Year")
        for col in "ABCDE":
            r.z(f"txtPg4IShed6_{i}{col}")
    r.a("txtPg4IShed6_13D", bv("nolco"))
    p6 = lambda o: [o["taxDueRegular"], o["specialRate"], o["shareOtherGovt"], o["netSpecial"], o["taxDue"]]  # noqa: E731
    for i in range(1, 6):
        r.a(f"txtPg4ISc6_{i}A", p6(A)[i - 1])
        r.a(f"txtPg4ISc6_{i}B", p6(B)[i - 1] if spouse else 0)
    p7 = lambda o: {1: o["excess"], 2: o["prevPaid"], 5: o["taxWithheldComp"], 10: o["credits"]}  # noqa: E731
    for i in range(1, 9):
        r.a(f"txtPg4IPart7_{i}A", p7(A).get(i, ZERO))
        r.a(f"txtPg4IPart7_{i}B", p7(B).get(i, ZERO) if spouse else 0)
    r.e("txtPg4IPart7_9Specify")
    r.z("txtPg4IPart7_9A")
    r.z("txtPg4IPart7_9B")
    r.a("txtPg4IPart7_10A", A["credits"])
    r.a("txtPg4IPart7_10B", bv("credits"))
    for i in range(1, 11):
        r.z(f"txtPg4IPart8_{i}A")
        r.z(f"txtPg4IPart8_{i}B")
    ixv = lambda n, s: inc.w(data, f"ix{n}{s}") if s == "A" or spouse else ZERO  # noqa: E731
    r.a("txtPg4IPart9_1A", ixv(1, "A"))
    r.a("txtPg4IPart9_1B", ixv(1, "B"))
    for i in (2, 3, 4):
        r.enc(f"txtPg4IPart9_{i}Particulars", data.get(f"ix{i}descA"))
        r.a(f"txtPg4IPart9_{i}A", ixv(i, "A"))
        r.a(f"txtPg4IPart9_{i}B", ixv(i, "B"))
    r.a("txtPg4IPart9_5A", A["ixTotalAdd"])
    r.a("txtPg4IPart9_5B", bv("ixTotalAdd"))
    for i in (6, 7, 8, 9):
        r.enc(f"txtPg4IPart9_{i}Particulars", data.get(f"ix{i}descA"))
        r.a(f"txtPg4IPart9_{i}A", ixv(i, "A"))
        r.a(f"txtPg4IPart9_{i}B", ixv(i, "B"))
    r.a("txtPg4IPart9_10A", A["ixTotalLess"])
    r.a("txtPg4IPart9_10B", bv("ixTotalLess"))
    r.a("txtPg4IPart9_11A", A["ixNetTaxable"])
    r.a("txtPg4IPart9_11B", bv("ixNetTaxable"))
    # the attachment pages (1701-M, financial statements): blank, as the package writes them
    r.p("txtPg1mTIN1", t["t1"])
    r.p("txtPg1mTIN2", t["t2"])
    r.p("txtPg1mTIN3", t["t3"])
    r.p("txtPg1mBranchCode", t["branch3"])
    r.p("txtPg1mTaxpayerName", raw)
    r.b("rdoPg1mOption1", True)
    r.b("rdoPg1mOption2", False)
    for i in (1, 2, 3):
        for col in "ABCDEF":
            r.e(f"txtPg1mI{i}{col}SchdA")
    r.z("txtPg1mI4BSchdA")
    r.z("txtPg1mI4ESchdA")
    for i in (5, 6):
        for col in "ABCDEF":
            r.e(f"txtPg1mI{i}{col}SchdA")
    full = lambda i: [r.z(f"txtPg1mI{i}{col}SchdB") for col in "ABCDEFGH"]  # noqa: E731
    cdgh = lambda i: [r.z(f"txtPg1mI{i}{col}SchdB") for col in "CDGH"]  # noqa: E731
    for i in (1, 2, 3, 4, 5, 6, 7):
        full(i)
    cdgh(8)
    full(9)
    cdgh(10)
    full(11)
    r.e("txtPg1mI12DescSchdB")
    full(12)
    r.e("txtPg1mI13DescSchdB")
    full(13)
    cdgh(14)
    full(15)
    full(16)
    full(17)
    r.p("txtPg2mTIN1", t["t1"])
    r.p("txtPg2mTIN2", t["t2"])
    r.p("txtPg2mTIN3", t["t3"])
    r.p("txtPg2mBranchCode", t["branch3"])
    r.p("txtPg2mTaxpayerName", raw)
    for i in range(1, 17):
        for col in "ABCD":
            r.z(f"txtPg2mI{i}{col}SchdC")
    for x in ("a", "b", "c"):
        for col in "ABCD":
            r.z(f"txtPg2mI17{x}{col}SchdC")
    r.e("txtPg2mI17dDescSchdC")
    for col in "ABCD":
        r.z(f"txtPg2mI17d{col}SchdC")
    for col in "ABCD":
        r.z(f"txtPg2mI18{col}SchdC")
    for i in (1, 2, 3, 4):
        r.e(f"txtPg2mI{i}DescSchdD")
        r.e(f"txtPg2mI{i}LBSchdD")
        r.z(f"txtPg2mI{i}ASchdD")
        r.z(f"txtPg2mI{i}BSchdD")
    r.z("txtPg2mI5ASchdD")
    r.z("txtPg2mI5BSchdD")
    r.g("attachmentCurrent", "1")
    r.g("attachmentTotal", "0")
    r.p("txtPg3mTIN1", t["t1"])
    r.p("txtPg3mTIN2", t["t2"])
    r.p("txtPg3mTIN3", t["t3"])
    r.p("txtPg3mBranchCode", t["branch3"])
    r.p("txtPg3mTaxpayerName", raw)
    r.b("rdoPg3mExemptTYPE", False)
    r.b("rdoPg3mSpecialRateTYPE", False)
    for i in (1, 2, 3):
        r.e(f"txtPg3mSchedA_{i}ATYPE")
        r.e(f"txtPg3mSchedA_{i}BTYPE")
    r.z("txtPg3mSchedA_4ATYPE")
    r.z("txtPg3mSchedA_4BTYPE")
    for i in (5, 6):
        r.e(f"txtPg3mSchedA_{i}ATYPE")
        r.e(f"txtPg3mSchedA_{i}BTYPE")
    for i in range(1, 10):
        r.z(f"txtPg3mSchedB_{i}ATYPE")
        r.z(f"txtPg3mSchedB_{i}BTYPE")
    r.e("txtPg3mSchedB_10TYPE")
    r.z("txtPg3mSchedB_10ATYPE")
    r.z("txtPg3mSchedB_10BTYPE")
    r.e("txtPg3mSchedB_11TYPE")
    r.z("txtPg3mSchedB_11ATYPE")
    r.z("txtPg3mSchedB_11BTYPE")
    for i in (12, 13):
        r.z(f"txtPg3mSchedB_{i}ATYPE")
        r.z(f"txtPg3mSchedB_{i}BTYPE")
    r.p("txtPg3mSchedB_14ATYPE", "0.0")
    r.p("txtPg3mSchedB_14BTYPE", "0.0")
    r.z("txtPg3mSchedB_15ATYPE")
    r.z("txtPg3mSchedB_15BTYPE")
    for i in (1, 2, 3):
        r.z(f"txtPg3mSchedC_{i}ATYPE")
        r.z(f"txtPg3mSchedC_{i}BTYPE")
    r.p("txtPg4mTIN1", t["t1"])
    r.p("txtPg4mTIN2", t["t2"])
    r.p("txtPg4mTIN3", t["t3"])
    r.p("txtPg4mBranchCode", t["branch3"])
    r.p("txtPg4mTaxpayerName", raw)
    for i in range(4, 17):
        r.z(f"txtPg4mSchedC_{i}ATYPE")
        r.z(f"txtPg4mSchedC_{i}BTYPE")
    for x in ("a", "b", "c"):
        r.z(f"txtPg4mSchedC_17{x}ATYPE")
        r.z(f"txtPg4mSchedC_17{x}BTYPE")
    r.e("txtPg4mSchedC_17dTYPE")
    r.z("txtPg4mSchedC_17dATYPE")
    r.z("txtPg4mSchedC_17dBTYPE")
    r.z("txtPg4mSchedC_18ATYPE")
    r.z("txtPg4mSchedC_18BTYPE")
    for i in (1, 2, 3, 4):
        r.e(f"txtPg4mSchedD1_{i}TYPE")
        r.e(f"txtPg4mSchedD1_{i}ALBTYPE")
        r.z(f"txtPg4mSchedD1_{i}ATYPE")
    r.z("txtPg4mSchedD1_5ATYPE")
    r.e("txtPg4mSchedD2_6TYPE")
    r.e("txtPg4mSchedD2_6BLBTYPE")
    r.z("txtPg4mSchedD2_6BTYPE")
    r.e("txtPg4mSchedD2_7TYPE")
    r.e("txtPg4mSchedD2_7BLBTYPE")
    r.z("txtPg4mSchedD2_7BTYPE")
    r.e("txtPg4mSchedD2_8TYPE")
    r.e("txtPg4mSchedD2_8LBBTYPE")
    r.z("txtPg4mSchedD2_8BTYPE")
    r.e("txtPg4mSchedD2_9TYPE")
    r.e("txtPg4mSchedD2_9BLBTYPE")
    r.z("txtPg4mSchedD2_9BTYPE")
    r.z("txtPg4mSchedD2_10BTYPE")
    r.p("txtCurrentPage", "1")
    r.p("txtMaxPage", "4")
    for k in ("txtZIP", "txtEnabledInputsOnValidation", "txtDisabledInputs", "txtEnabledLinks", "txtIsSpouseDisabled"):
        r.e(k)
    r.p("txtIsTaxFilerDisabled", "FALSE")
    for k in ("txtAttachmentTypes", "txtTIN4", "txtDisabledOnSave", "txtEnabledOnSave"):
        r.e(k)
    r.p("txtVersion", "051414")
    r.e("txtdisabledID")
    for k in ("rdoEXAttachmentTF", "rdoEXAttachmentS", "rdoSPAttachmentTF", "rdoSPAttachmentS"):
        r.b(k, False)
    inc.trailer(r, ctx.final, "N")
    r.enc("txtLineBus", inc.s(data.get("lineBus")) or c.get("ph_line_of_business"))
    r.g("driveSelectTPExport", "0")
    name = f"{t['t1']}{t['t2']}{t['t3']}{t['branch3']}1701v2018{mm}{p.year}.xml"
    return r.out, name


def write_export(rows: list[tuple[str, str]]) -> str:
    return inc.write_1701(rows)


def key_figures(comp: list[dict]) -> dict[str, Decimal]:
    c = inc.payload(comp)
    return {"tax_due": c["A"]["taxDue"], "credits": c["A"]["credits"], "payable": c["aggregate"]}
