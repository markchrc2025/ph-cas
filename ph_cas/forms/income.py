"""Shared pieces of the income-tax returns (1701Q, 1701, 1701A, 1702Q, 1702-RT):
the graduated tax tables, the taxpayer-background helpers, the books feed from
the tax engine (ph_cas.tax.income_tax) split into quarters, the row writer and
the five export layouts the eBIRForms package writes for these forms.

Whole pesos throughout: every typed or fed figure is rounded half up once at
the line (money.whole_peso); derived figures are sums of whole pesos.
"""

from datetime import date
from decimal import Decimal

from ph_cas.forms.engine import Context
from ph_cas.forms.export import ExportRefusal, amt, enc, tin_parts
from ph_cas.forms.money import ZERO, dec, whole_peso
from ph_cas.forms.needs import Need, draft_need

# ---- the graduated tables (Sec. 24(A)(2), TRAIN) ----------------------------------
# (upper bound, fixed tax, rate on the excess, lower bound)
TABLE_1 = [  # 2018 to 2022
    (Decimal(250000), ZERO, ZERO, ZERO),
    (Decimal(400000), ZERO, Decimal("0.20"), Decimal(250000)),
    (Decimal(800000), Decimal(30000), Decimal("0.25"), Decimal(400000)),
    (Decimal(2000000), Decimal(130000), Decimal("0.30"), Decimal(800000)),
    (Decimal(8000000), Decimal(490000), Decimal("0.32"), Decimal(2000000)),
    (None, Decimal(2410000), Decimal("0.35"), Decimal(8000000)),
]
TABLE_2 = [  # 2023 onward
    (Decimal(250000), ZERO, ZERO, ZERO),
    (Decimal(400000), ZERO, Decimal("0.15"), Decimal(250000)),
    (Decimal(800000), Decimal(22500), Decimal("0.20"), Decimal(400000)),
    (Decimal(2000000), Decimal(102500), Decimal("0.25"), Decimal(800000)),
    (Decimal(8000000), Decimal(402500), Decimal("0.30"), Decimal(2000000)),
    (None, Decimal(2202500), Decimal("0.35"), Decimal(8000000)),
]
EIGHT = Decimal("0.08")
REDUCTION = Decimal(250000)


def graduated_tax(taxable, year: int) -> Decimal:
    """The tax on a taxable income under the table of the year, in whole pesos."""
    t = dec(taxable)
    if t <= 0:
        return ZERO
    table = TABLE_1 if int(year) <= 2022 else TABLE_2
    for upper, fixed, rate, lower in table:
        if upper is None or t <= upper:
            return whole_peso(fixed + (t - lower) * rate)
    return ZERO


# ---- taxpayer background -------------------------------------------------------------
ATC = {
    "1701": ["II012", "II014", "II013", "II011", "II015", "II017", "II016"],
    "1701A": ["II012", "II014", "II015", "II017"],
    "1701Q": ["II012", "II014", "II013", "II015", "II017", "II016"],
    "1702Q": ["IC055"],
    "1702-RT": ["IC055"],
}
ATC_ITEM = {"1701": "7", "1701A": "7", "1701Q": "8", "1702Q": "5", "1702-RT": "5"}


def chosen_atc(raw, form: str) -> str:
    code = "".join(str(raw or "").split()).upper()
    if not code:
        return ""
    if code not in ATC[form]:
        item = ATC_ITEM[form]
        raise ExportRefusal(f"Item {item}: the ATC {code} is not one of the ATC choices printed on BIR Form {form}. Choose Item {item} again, or clear it, then try again.")
    return code


def taxpayer_type(c: dict) -> str:
    """"single" (single proprietorship) or "prof" (professional) from the Company, else ""."""
    k = " ".join(str(c.get("ph_individual_type") or "").split()).lower()
    return {"professional": "prof", "single proprietorship": "single"}.get(k, "")


def civil_status(c: dict) -> str:
    k = "".join(ch for ch in str(c.get("ph_civil_status") or "").lower() if ch.isalpha())
    return {"single": "single", "married": "married", "legallyseparated": "separated", "widower": "widow", "widow": "widow", "widowed": "widow"}.get(k, "")


def s(v) -> str:
    return "" if v is None else str(v).strip()


def individual(c: dict) -> bool:
    return (c.get("ph_taxpayer_type") or "") == "Individual"


def name_given(c: dict) -> str:
    """1701 and 1701A: "LAST, FIRST MIDDLE"; a non-individual's registered name."""
    if individual(c):
        given = " ".join(x for x in (s(c.get("ph_first_name")), s(c.get("ph_middle_name"))) if x)
        return ", ".join(x for x in (s(c.get("ph_last_name")), given) if x)
    return s(c.get("ph_registered_name")) or s(c.get("company_name"))


def name_commas(c: dict) -> str:
    """1701Q: "LAST, FIRST, MIDDLE"."""
    if individual(c):
        return ", ".join(x for x in (s(c.get("ph_last_name")), s(c.get("ph_first_name")), s(c.get("ph_middle_name"))) if x)
    return s(c.get("ph_registered_name")) or s(c.get("company_name"))


def name_raw(c: dict) -> str:
    """Pages 2 to 4 of the individual returns print the last name alone, unencoded."""
    return s(c.get("ph_last_name")) if individual(c) else (s(c.get("ph_registered_name")) or s(c.get("company_name")))


def name_reg(c: dict) -> str:
    """1702Q and 1702-RT: the registered name ("LAST, FIRST" for an individual)."""
    if individual(c):
        return ", ".join(x for x in (s(c.get("ph_last_name")), s(c.get("ph_first_name"))) if x)
    return s(c.get("ph_registered_name")) or s(c.get("company_name"))


def address(c: dict) -> str:
    return " ".join(s(c.get("ph_registered_address")).split())


def birth_parts(v) -> tuple[str, str, str]:
    p = s(v).split("-")
    return (p[1], p[2], p[0]) if len(p) == 3 else ("", "", "")


def slash_date(v) -> str:
    p = s(v).split("-")
    return f"{p[1]}/{p[2]}/{p[0]}" if len(p) == 3 else s(v)


def spouse_tin(data: dict) -> str:
    return "".join(ch for ch in s(data.get("spouseTin")) if ch.isdigit())


# ---- books -------------------------------------------------------------------------------
def _engine(company: str, start, end, annual: bool) -> dict[str, Decimal]:
    from ph_cas.tax.income_tax import compute_income_tax

    return {item: dec(amount) for item, _label, amount, _src in compute_income_tax(company, str(start), str(end), annual)}


def annual(company: str, start: date, end: date) -> dict[str, Decimal]:
    return _engine(company, start, end, annual=True)


def quarter_figures(company: str, ctx: Context) -> tuple[dict, dict, list[dict]]:
    """(this quarter, up to the previous quarter, every quarter so far): each a dict of
    the engine's items. Quarterly returns are cumulative, so the quarter's own figures
    are the year-to-date less the year-to-date at the previous quarter's end."""
    from ph_cas.forms.period import fiscal_start_month, quarter_range

    p = ctx.period
    sm = fiscal_start_month(ctx.company.get("ph_fiscal_year_start")) if p.fiscal else 1
    series: list[dict] = []
    this: dict[str, Decimal] = {}
    prev: dict[str, Decimal] = {}
    cum_prev: dict[str, Decimal] = {}
    for q in range(1, p.quarter_no + 1):
        qs, qe = quarter_range(p.year, q, sm)
        cum = _engine(company, qs, qe, annual=False)  # the engine runs from 1 January to the quarter's end
        own = {k: cum.get(k, ZERO) - cum_prev.get(k, ZERO) for k in cum}
        series.append(own)
        if q == p.quarter_no:
            this = own
        else:
            prev = cum
        cum_prev = cum
    return this, prev, series


def peso_text(d) -> str:
    """What a fed figure is stored as: whole pesos, "12345"."""
    return str(whole_peso(dec(d)))


def nonneg_peso(d) -> Decimal:
    v = whole_peso(dec(d))
    return v if v > 0 else ZERO


def books_line(key: str, label: str, amount, company: str, start, end, doctype: str = "sales-invoice") -> dict:
    return {"key": key, "label": label, "amount": peso_text(amount), "records": 0, "filter": f"/app/{doctype}?company={company}&docstatus=1&posting_date=%5B%22Between%22%2C%5B%22{start}%22%2C%22{end}%22%5D%5D"}


# ---- lines ---------------------------------------------------------------------------------
def line(item: str, label: str, amount, kind: str) -> dict:
    return {"item": item, "label": label, "amount": whole_peso(dec(amount)), "kind": kind}


def kinds(data: dict):
    books = (data.get("_source") or {}).get("books") or {}

    def kind(key: str) -> str:
        return "books" if key in books and str(data.get(key)) == str(books[key]) else "typed"

    return kind


def w(data: dict, key: str) -> Decimal:
    return whole_peso(dec(data.get(key)))


def hidden(key: str, payload: dict) -> dict:
    return {"item": key, "label": "", "amount": ZERO, "kind": "derived", "c": payload}


def payload(comp: list[dict]) -> dict:
    return next(ln for ln in comp if ln["item"] == "_c")["c"]


def neg(v) -> bool:
    return dec(v) < 0


# ---- needs ---------------------------------------------------------------------------------
def common_needs(data: dict, ctx: Context, form: str, overpaid: bool) -> list[Need]:
    out = []
    c = ctx.company
    # the 1702Q and 1702-RT set Item 5 from the computation (the higher of MCIT and the regular tax)
    if form not in ("1702Q", "1702-RT") and not s(data.get("atc")):
        out.append(draft_need(ctx.return_name, "atc", f"Which ATC applies (Item {ATC_ITEM[form]}: {', '.join(ATC[form])})?", "The return marks one ATC.", "choice", list(ATC[form])))
    if individual(c) and form != "1702Q" and form != "1702-RT" and not taxpayer_type(c):
        out.append(Need("company.individual_type", "Is the taxpayer a single proprietor or a professional?", f"The BIR {form} marks the taxpayer type.", f"/app/company/{c.get('name')}", "choice", ["Single Proprietorship", "Professional"]))
    if overpaid and s(data.get("over")) not in ("refund", "tcc", "carry"):
        out.append(draft_need(ctx.return_name, "over", "The return shows an overpayment. Is it to be refunded, issued a Tax Credit Certificate, or carried over?", "The return marks one box.", "choice", ["refund", "tcc", "carry"]))
    if individual(c) and form in ("1701", "1701A") and civil_status(c) == "married":
        if s(data.get("spouseIncome")) not in ("yes", "no"):
            out.append(draft_need(ctx.return_name, "spouseIncome", "Does the spouse have income?", "Item 17 marks yes or no for a married taxpayer.", "choice", ["yes", "no"]))
        if s(data.get("filing")) not in ("joint", "separate"):
            out.append(draft_need(ctx.return_name, "filing", "Is the filing joint or separate?", "Item 18 marks one box for a married taxpayer.", "choice", ["joint", "separate"]))
    return out


# ---- rows and layouts -------------------------------------------------------------------------
class Rows:
    """The export rows of one form, in the package's order."""

    def __init__(self, ns: str):
        self.ns = ns
        self.out: list[tuple[str, str]] = []

    def p(self, k: str, v):
        self.out.append((self.ns + k, "" if v is None else str(v)))

    def g(self, k: str, v):
        self.out.append((k, "" if v is None else str(v)))

    def b(self, k: str, cond):
        self.p(k, "true" if cond else "false")

    def a(self, k: str, d):
        self.p(k, amt(d))

    def z(self, k: str):
        self.p(k, amt(0))

    def e(self, k: str):
        self.p(k, "")

    def enc(self, k: str, v):
        self.p(k, enc(s(v)))


def tin(c: dict) -> dict:
    return tin_parts(c.get("tax_id") or "", c.get("ph_branch_code") or "00000")


def payments(r: Rows, data: dict):
    """Items 32 to 35 of the 1701Q and 1701A: the payment particulars."""
    pay = lambda k: amt(data[k]) if s(data.get(k)) else ""  # noqa: E731
    r.enc("txtAgency32", data.get("p32bank"))
    r.enc("txtNumber32", data.get("p32num"))
    r.enc("txtDate32", data.get("p32date"))
    r.p("txtAmount32", pay("p32amt"))
    r.enc("txtAgency33", data.get("p33bank"))
    r.enc("txtNumber33", data.get("p33num"))
    r.enc("txtDate33", data.get("p33date"))
    r.p("txtAmount33", pay("p33amt"))
    r.enc("txtNumber34", data.get("p34num"))
    r.enc("txtDate34", data.get("p34date"))
    r.p("txtAmount34", pay("p34amt"))
    r.enc("txtParticular35", data.get("p35particular"))
    r.enc("txtAgency35", data.get("p35bank"))
    r.enc("txtNumber35", data.get("p35num"))
    r.enc("txtDate35", data.get("p35date"))
    r.p("txtAmount35", pay("p35amt"))


def trailer(r: Rows, final: bool, enroll: str = "Y"):
    r.g("txtFinalFlag", "1" if final else "0")
    r.g("txtEnroll", enroll)
    r.g("ebirOnlineConfirmUsername", "")
    r.g("ebirOnlineUsername", "")
    r.g("ebirOnlineSecret", "")


PAY_INPUTS = [
    ("p32bank", "32 Cash/bank debit memo: bank", "text"),
    ("p32num", "32 number", "text"),
    ("p32date", "32 date (MM/DD/YYYY)", "text"),
    ("p32amt", "32 amount", "money"),
    ("p33bank", "33 Check: bank", "text"),
    ("p33num", "33 number", "text"),
    ("p33date", "33 date (MM/DD/YYYY)", "text"),
    ("p33amt", "33 amount", "money"),
    ("p34num", "34 Tax debit memo: number", "text"),
    ("p34date", "34 date (MM/DD/YYYY)", "text"),
    ("p34amt", "34 amount", "money"),
    ("p35particular", "35 Others: particulars", "text"),
    ("p35bank", "35 bank", "text"),
    ("p35num", "35 number", "text"),
    ("p35date", "35 date (MM/DD/YYYY)", "text"),
    ("p35amt", "35 amount", "money"),
]
SPOUSE_INPUTS = [
    ("spouseName", "Spouse: name", "text"),
    ("spouseTin", "Spouse: TIN (9 digits)", "text"),
    ("spouseRdo", "Spouse: RDO code", "text"),
    ("spouseType", "Spouse: taxpayer type", "select:single,prof,comp"),
    ("spouseAtc", "Spouse: ATC", "text"),
    ("spouseCitizenship", "Spouse: citizenship", "text"),
    ("spouseContact", "Spouse: contact number", "text"),
    ("spouseForeignCredit", "Spouse: claiming foreign tax credits", "select:no,yes"),
    ("spouseForeignTaxNo", "Spouse: foreign tax number", "text"),
]


def write_1701q(rows: list[tuple[str, str]]) -> str:
    body = "\n".join(f"            <div>{k}={v}{k}=</div>\t" for k, v in rows)
    return "<?xml version='1.0'?>\t\n" + body + "\n            \t\n            All Rights Reserved BIR 2012.0"


def write_1702(rows: list[tuple[str, str]], tail_year: str = "2012.0") -> str:
    """The 1702Q (2012.0) and 1702-RT (2014.0) layout: CR LF endings."""
    lead = "            "
    body = "\n".join(f"{lead}<div>{k}={v}{k}=</div>\t\r" for k, v in rows)
    return "<?xml version='1.0'?>\t\r\n" + body + "\n" + f"{lead}\t\r\n{lead}All Rights Reserved BIR {tail_year}"


def write_1701(rows: list[tuple[str, str]]) -> str:
    body = "\n".join(f"            <div>{k}={v}{k}=</div>\t" for k, v in rows)
    return "<?xml version='1.0'?>\t\n" + body + "\n            \t\n            All Rights Reserved BIR 2012.0"


def write_1701a(rows: list[tuple[str, str]]) -> str:
    body = "\n".join(f"            <div>{k}={v}{k}=</div>  " for k, v in rows)
    return "<?xml version='1.0'?>  \n" + body + "\n              \n            All Rights Reserved BIR 2014."
