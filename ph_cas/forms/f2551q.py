"""BIR Form 2551Q, Quarterly Percentage Tax Return (January 2018 ENCS).

Data keys (the draft's `data`), after the Portal's editor:
  rows            [{atc, taxable, rate}]   Schedule 1, up to six rows (books: one row per ATC)
  i15             creditable percentage tax withheld per 2307 (books)
  i16             tax paid in the return previously filed, if amended (books from the original)
  i17, i17label   other credit and what it is (typed)
  i20, i21, i22   surcharge, interest, compromise (typed)
  over            "refund" or "tcc" when Item 24 is an overpayment (typed)
  taxRelief, taxReliefSpec, itRate ("graduated" or "eight"), sheets, pay25..28*, taxAgent* (typed)
Derived (never stored): each row's due, Items 14, 18, 19, 23, 24.
Whole pesos: the paper says do not enter centavos.
"""

from decimal import Decimal

import frappe

from ph_cas.forms.engine import Context
from ph_cas.forms.export import ExportRefusal, amt, enc, file_name, rb, tin_parts
from ph_cas.forms.money import ZERO, dec, nonneg, text, whole_peso
from ph_cas.forms.needs import Need, draft_need

NS = "frm2551Qv2018:"
# The eBIRForms Schedule 1 dropdown, 1-based, in the package's order; 0 is an empty line.
ATC_INDEX = {"PT010": 1, "PT040": 2, "PT041": 3, "PT060": 4, "PT070": 5, "PT090": 6, "PT120": 7, "PT130": 8}
SCHEDULE_1_ROWS = 6
INPUTS = [
    ("i16", "16 Tax paid in return previously filed (amended)", "money"),
    ("i17", "17 Other tax credit or payment", "money"),
    ("i17label", "17 specify", "text"),
    ("i20", "20 Surcharge", "money"),
    ("i21", "21 Interest", "money"),
    ("i22", "22 Compromise", "money"),
    ("over", "Overpayment: refund or TCC", "select:refund,tcc"),
    ("taxRelief", "Availing of tax relief (Item 12)", "select:no,yes"),
    ("taxReliefSpec", "Relief: specify (Item 12A)", "text"),
    ("itRate", "Item 13 income tax rate (individuals, Q1)", "select:graduated,eight"),
    ("sheets", "Number of sheets attached", "text"),
    ("taxAgentNo", "Tax agent accreditation number", "text"),
    ("taxAgentIssue", "Tax agent date of issue (MM/DD/YYYY)", "text"),
    ("taxAgentExpiry", "Tax agent expiry date (MM/DD/YYYY)", "text"),
    ("pay25bank", "25 Cash/bank debit memo: bank", "text"),
    ("pay25num", "25 number", "text"),
    ("pay25date", "25 date (MM/DD/YYYY)", "text"),
    ("pay25amt", "25 amount", "money"),
    ("pay26bank", "26 Check: bank", "text"),
    ("pay26num", "26 number", "text"),
    ("pay26date", "26 date", "text"),
    ("pay26amt", "26 amount", "money"),
    ("pay27bank", "27 Tax debit memo: agency", "text"),
    ("pay27num", "27 number", "text"),
    ("pay27date", "27 date", "text"),
    ("pay27amt", "27 amount", "money"),
    ("pay28particular", "28 Others: particulars", "text"),
    ("pay28bank", "28 agency", "text"),
    ("pay28num", "28 number", "text"),
    ("pay28date", "28 date", "text"),
    ("pay28amt", "28 amount", "money"),
]
SCHEDULES = {"rows": ("Schedule 1: percentage tax by ATC (6 rows on the paper)", ["ATC", "Taxable amount", "Rate %"], ["atc", "taxable", "rate"])}
CREATE_WINDOW = ("2020-07-01", "2023-06-30")


# ---- books -------------------------------------------------------------------------
def feed(ctx: Context) -> dict:
    """Schedule 1 from the quarter's posted sales subject to percentage tax (one row, the
    company's ATC at the rate in force on the quarter's last day), Item 15 from the 2307s
    received for the quarter, Item 16 from the original return when this one amends it."""
    from ph_cas.tax.rules import resolve

    company = ctx.company["name"]
    start, end = ctx.period.start, ctx.period.end
    atc = (ctx.company.get("ph_pt_atc") or "PT010").strip().upper()
    sales = frappe.db.sql(
        """select coalesce(sum(ph_pt_base), 0), count(*) from `tabSales Invoice`
           where company = %s and docstatus = 1 and posting_date between %s and %s and ifnull(ph_pt_base, 0) != 0""",
        (company, start, end),
    )[0]
    base_exact, n_sales = dec(sales[0]), int(sales[1])
    rule = resolve("percentage", end, atc)
    rate = dec(rule.rate)
    warnings: list[str] = []
    if base_exact < 0:
        warnings.append(f"The books total for Schedule 1 is below zero ({base_exact}); it is shown as 0.")
    base = whole_peso(nonneg(base_exact))
    withheld = frappe.db.sql(
        """select coalesce(sum(l.tax_withheld), 0), count(distinct d.name) from `tabPH 2307 Received Line` l
           join `tabPH 2307 Received` d on d.name = l.parent
           where d.docstatus = 1 and d.company = %s and l.kind = 'Percentage tax' and d.period_from >= %s and d.period_to <= %s""",
        (company, start, end),
    )[0]
    i15 = whole_peso(nonneg(dec(withheld[0])))
    if str(start) <= CREATE_WINDOW[1] and str(end) >= CREATE_WINDOW[0]:
        warnings.append("This quarter falls in the CREATE window (1 July 2020 to 30 June 2023, 1 percent); check the rate on each row.")
    figures = {"rows": [{"atc": atc, "taxable": text(base, 0), "rate": text(rate, 1)}], "i15": text(i15, 0)}
    lines = [
        {"key": f"rows.{atc}", "label": f"Schedule 1, {atc} at {rate}% ({rule.rule_id})", "amount": text(base, 0), "records": n_sales, "filter": f"/app/sales-invoice?company={company}&docstatus=1&posting_date=%5B%22Between%22%2C%5B%22{start}%22%2C%22{end}%22%5D%5D"},
        {"key": "i15", "label": "Item 15, percentage tax withheld per 2307", "amount": text(i15, 0), "records": int(withheld[1]), "filter": f"/app/ph-2307-received?company={company}&docstatus=1"},
    ]
    if ctx.extra.get("amends"):
        prev = frappe.db.get_value("PH Tax Return Line", {"parent": ctx.extra["amends"], "item": "24"}, "amount") or 0
        figures["i16"] = text(whole_peso(nonneg(dec(prev))), 0)
        lines.append({"key": "i16", "label": "Item 16, tax paid in the return previously filed", "amount": figures["i16"], "records": 1, "filter": f"/app/ph-tax-return/{ctx.extra['amends']}"})
    return {"figures": figures, "lines": lines, "warnings": warnings}


# ---- compute -----------------------------------------------------------------------
def compute(data: dict, ctx: Context) -> list[dict]:
    rows = data.get("rows") or []
    out: list[dict] = []
    kind_of = _kinds(data)
    total_due = ZERO
    dues = []
    for i, r in enumerate(rows[:SCHEDULE_1_ROWS], start=1):
        taxable, rate = dec(r.get("taxable")), dec(r.get("rate"))
        due = whole_peso(taxable * rate / 100)
        dues.append(due)
        total_due += due
        atc = (r.get("atc") or "").strip().upper()
        out.append({"item": f"S1.{i} base", "label": f"Schedule 1 row {i}: taxable amount ({atc or 'no ATC'})", "amount": taxable, "kind": kind_of("rows")})
        out.append({"item": f"S1.{i} rate", "label": f"Schedule 1 row {i}: rate %", "amount": rate, "kind": kind_of("rows")})
        out.append({"item": f"S1.{i} tax", "label": f"Schedule 1 row {i}: tax due", "amount": due, "kind": "derived"})
    i = {}
    i[14] = total_due
    i[15] = whole_peso(dec(data.get("i15")))
    i[16] = whole_peso(dec(data.get("i16")))
    i[17] = whole_peso(dec(data.get("i17")))
    i[18] = i[15] + i[16] + i[17]
    i[19] = i[14] - i[18]
    i[20] = whole_peso(dec(data.get("i20")))
    i[21] = whole_peso(dec(data.get("i21")))
    i[22] = whole_peso(dec(data.get("i22")))
    i[23] = i[20] + i[21] + i[22]
    i[24] = i[19] + i[23]
    labels = {
        14: "Total Tax Due", 15: "Creditable Percentage Tax Withheld per BIR Form No. 2307", 16: "Tax Paid in Return Previously Filed, if this is an Amended Return",
        17: f"Other Tax Credit/Payment ({data.get('i17label') or 'specify'})", 18: "Total Tax Credits/Payments", 19: "Tax Still Payable/(Overpayment)",
        20: "Surcharge", 21: "Interest", 22: "Compromise", 23: "Total Penalties", 24: "TOTAL AMOUNT PAYABLE/(Overpayment)",
    }
    derived = {14, 18, 19, 23, 24}
    for n in range(14, 25):
        out.append({"item": str(n), "label": labels[n], "amount": i[n], "kind": "derived" if n in derived else kind_of(f"i{n}")})
    out.append({"item": "_dues", "label": "", "amount": ZERO, "kind": "derived", "dues": dues, "i": i})
    return out


def _kinds(data: dict):
    books = (data.get("_source") or {}).get("books") or {}

    def kind(key: str) -> str:
        if key in books and data.get(key) == books[key]:
            return "books"
        return "typed"

    return kind


def _comp(lines: list[dict]) -> dict:
    return next(ln for ln in lines if ln["item"] == "_dues")


# ---- needs -------------------------------------------------------------------------
def needs(data: dict, ctx: Context) -> list[Need]:
    out: list[Need] = []
    rows = data.get("rows") or []
    for n, r in enumerate(rows, start=1):
        code = (r.get("atc") or "").strip().upper()
        if not code and dec(r.get("taxable")) != 0:
            out.append(draft_need(ctx.return_name, f"rows.{n}.atc", f"Schedule 1, row {n} has an amount but no ATC. Which ATC is it?", "The eBIRForms file carries each row by its ATC.", "atc", list(ATC_INDEX)))
        elif code and code not in ATC_INDEX:
            out.append(draft_need(ctx.return_name, f"rows.{n}.atc", f"Schedule 1, row {n}: the ATC {code} is not one the 2551Q lists. Which ATC is it?", "The eBIRForms file lists eight ATCs for Schedule 1.", "atc", list(ATC_INDEX)))
    if len([r for r in rows if (r.get("atc") or "").strip() or dec(r.get("taxable")) != 0]) > SCHEDULE_1_ROWS:
        out.append(draft_need(ctx.return_name, "rows", f"Schedule 1 has room for {SCHEDULE_1_ROWS} rows; the draft has more. Which rows are combined or removed?", "The form cannot carry more rows.", "text"))
    comp = _comp(compute(data, ctx))["i"]
    if comp[24] < 0 and (data.get("over") or "") not in ("refund", "tcc"):
        out.append(draft_need(ctx.return_name, "over", "Item 24 is an overpayment. Is it to be refunded or issued a Tax Credit Certificate?", "The form marks one box for an overpayment.", "choice", ["refund", "tcc"]))
    if dec(data.get("i17")) != 0 and not (data.get("i17label") or "").strip():
        out.append(draft_need(ctx.return_name, "i17label", "Item 17 has an amount. What is the other tax credit or payment?", "Item 17 asks to specify.", "text"))
    if (data.get("taxRelief") or "") == "yes" and not (data.get("taxReliefSpec") or "").strip():
        out.append(draft_need(ctx.return_name, "taxReliefSpec", "Which special law or international tax treaty gives the relief?", "Item 12A asks to specify.", "text"))
    if ctx.company.get("ph_taxpayer_type") == "Individual" and ctx.period.quarter_no == 1 and (data.get("itRate") or "") not in ("graduated", "eight"):
        out.append(draft_need(ctx.return_name, "itRate", "Which income tax rate does the taxpayer avail of this year: graduated, or 8 percent on gross?", "Item 13 is answered by an individual in the first quarter.", "choice", ["graduated", "eight"]))
    return out


# ---- export ------------------------------------------------------------------------
def _full_name(c: dict) -> str:
    if (c.get("ph_taxpayer_type") or "") == "Individual":
        given = " ".join(x for x in (c.get("ph_first_name"), c.get("ph_middle_name")) if x)
        return ", ".join(x for x in (c.get("ph_last_name"), given) if x)
    return c.get("ph_registered_name") or c.get("company_name") or ""


def _rate1(v) -> str:
    return f"{dec(v):.1f}"


def _assert_encodable(rows: list[dict]):
    for i, r in enumerate(rows, start=1):
        code = (r.get("atc") or "").strip().upper()
        if not code and dec(r.get("taxable")) == 0:
            continue
        if not code:
            raise ExportRefusal(f"Schedule 1, row {i} has an amount but no ATC. Choose its ATC or remove the row, then export again.")
        if code not in ATC_INDEX:
            raise ExportRefusal(f"Schedule 1, row {i}: the ATC {code} cannot be written into the eBIRForms export. Change the row's ATC or remove the row, then export again.")
        if i > SCHEDULE_1_ROWS:
            raise ExportRefusal(f"Schedule 1, row {i}: the form has room for {SCHEDULE_1_ROWS} rows. Move it into an empty row or remove it, then export again.")


def export_rows(data: dict, comp: list[dict], ctx: Context) -> tuple[list[tuple[str, str]], str]:
    c = ctx.company
    t = tin_parts(c.get("tax_id") or "", c.get("ph_branch_code") or "00000")
    yyyy = str(ctx.period.year)
    qn = ctx.period.quarter_no
    sched = data.get("rows") or []
    _assert_encodable(sched)
    cm = _comp(comp)
    i, dues = cm["i"], cm["dues"]
    rows: list[tuple[str, str]] = []
    P = lambda k, v: rows.append((NS + k, v))  # noqa: E731
    G = lambda k, v: rows.append((k, v))  # noqa: E731

    P("forThe_1", rb(True))
    P("forThe_2", rb(False))
    P("rtnMonth", "12")
    P("txtYear", yyyy)
    for n in range(1, 5):
        P(f"qtr_{n}", rb(qn == n))
    P("amendedRtn_1", rb(ctx.is_amended))
    P("amendedRtn_2", rb(not ctx.is_amended))
    P("txtSheets", str(data.get("sheets") or "0"))
    P("txtTIN1", t["t1"])
    P("txtTIN2", t["t2"])
    P("txtTIN3", t["t3"])
    P("txtBranchCode", t["branch3"])
    P("txtRDOCode", c.get("ph_rdo") or "")
    P("registeredName", enc(_full_name(c)))
    P("registeredAddress", enc(" ".join((c.get("ph_registered_address") or "").split())))
    P("zipCode", c.get("ph_zip") or "")
    P("telNo", ctx.contact_number or c.get("ph_contact_number") or "")
    G("txtEmail", c.get("ph_email") or "")
    relief = (data.get("taxRelief") or "") == "yes"
    P("taxTreaty_1", rb(relief))
    P("taxTreaty_2", rb(not relief))
    P("txtTaxReliefSpecify", enc(data.get("taxReliefSpec")) or "0")
    it_rate = data.get("itRate") or "graduated"
    asks13 = (c.get("ph_taxpayer_type") or "") == "Individual" and qn == 1
    P("taxRate1", rb(asks13 and it_rate != "eight"))
    P("taxRate2", rb(asks13 and it_rate == "eight"))
    for n in range(14, 25):
        if n == 17:
            P("txt17Specify", enc(data.get("i17label")))
        P(f"txt{n}", amt(i[n]))
    P("overPayment1", rb((data.get("over") or "") == "refund"))
    P("overPayment2", rb((data.get("over") or "") == "tcc"))
    G("txtTaxAgentNo", enc(data.get("taxAgentNo")))
    G("txtDateIssue", enc(data.get("taxAgentIssue")))
    G("txtDateExpiry", enc(data.get("taxAgentExpiry")))
    for no in range(25, 29):
        if no == 28:
            P("txtParticular28", enc(data.get("pay28particular")))
        P(f"txtAgency{no}", enc(data.get(f"pay{no}bank")))
        P(f"txtNumber{no}", enc(data.get(f"pay{no}num")))
        P(f"txtDate{no}", enc(data.get(f"pay{no}date")))
        v = data.get(f"pay{no}amt")
        P(f"txtAmount{no}", amt(v) if v not in (None, "") else "")
    P("txtPg2TIN1", t["t1"])
    P("txtPg2TIN2", t["t2"])
    P("txtPg2TIN3", t["t3"])
    P("txtPg2BranchCode", t["branch3"])
    P("txtPg2TaxpayerName", _full_name(c))
    for n in range(SCHEDULE_1_ROWS):
        r = sched[n] if n < len(sched) else {}
        code = (r.get("atc") or "").strip().upper()
        idx = ATC_INDEX.get(code, 0)
        G(f"drpATC{n + 1}", str(idx))
        G(f"txtATCAmt{n + 1}", amt(r.get("taxable") if idx else 0))
        G(f"txtATCRate{n + 1}", _rate1(r.get("rate")) if idx else "0.00")
        G(f"txtATCDue{n + 1}", amt(dues[n] if idx and n < len(dues) else 0))
    G("txtTotalSched1", amt(i[14]))
    P("txtCurrentPage", "2")
    P("txtMaxPage", "2")
    G("txtFinalFlag", "1" if ctx.final else "0")
    G("txtEnroll", "Y")
    G("ebirOnlineConfirmUsername", "")
    G("ebirOnlineUsername", "")
    G("ebirOnlineSecret", "")
    G("driveSelectTPExport", "0")
    return rows, file_name(c.get("tax_id") or "", c.get("ph_branch_code") or "00000", "2551Q", "2018", "12", yyyy, qn)


def filed_snapshot_extra(data: dict, ctx: Context) -> dict:
    return {"schedule_1": data.get("rows") or []}


def key_figures(comp: list[dict]) -> dict[str, Decimal]:
    i = _comp(comp)["i"]
    return {"tax_due": i[14], "credits": i[18], "payable": i[24]}


__all__ = ["feed", "compute", "needs", "export_rows", "filed_snapshot_extra", "key_figures", "ATC_INDEX", "SCHEDULE_1_ROWS", "NS"]

