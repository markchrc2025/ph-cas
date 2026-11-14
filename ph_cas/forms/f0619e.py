"""BIR Form 0619-E, Monthly Remittance Form of Creditable Income Taxes Withheld,
Expanded (January 2018 ENCS). Printed on the blank; centavos exact.

Data: remittance (14, books), previouslyRemitted (15), surcharge, interest,
compromise (17A to C), amended, anyWithheld, category, dueDate, contact, email,
signatory and payment inputs. Derived: 16, 17D, 18.
"""

from datetime import date

import frappe
from frappe.utils import add_months, get_first_day

from ph_cas.forms import withholding as wh
from ph_cas.forms.engine import Context
from ph_cas.forms.money import centavos, dec, text
from ph_cas.forms.needs import Need, draft_need
from ph_cas.tax.calendar import next_working_day

INPUTS = [
    ("previouslyRemitted", "15 Less: amount remitted in previously filed form (amended)", "money"),
    ("surcharge", "17A Surcharge", "money"),
    ("interest", "17B Interest", "money"),
    ("compromise", "17C Compromise", "money"),
    ("dueDate", "Due date (yyyy-mm-dd, blank: the 10th of next month)", "text"),
] + wh.HEAD_INPUTS + wh.PAY_INPUTS
SCHEDULES = {}


def due_date(period_end: date) -> str:
    d = get_first_day(add_months(period_end, 1))
    d = d.replace(day=10)
    return str(next_working_day(d))


def feed(ctx: Context) -> dict:
    company = ctx.company["name"]
    start, end = ctx.period.start, ctx.period.end
    rows = wh.ewt_rows(company, start, end)
    total = sum((centavos(v["tax"]) for v in rows.values()), centavos(0))
    warnings = []
    if ctx.period.n % 3 == 0:
        warnings.append("The third month of a quarter is remitted on the 1601-EQ, not on a 0619-E.")
    n = frappe.db.count("Purchase Invoice", {"company": company, "docstatus": 1, "posting_date": ["between", [start, end]]})
    lines = [{"key": "remittance", "label": "Item 14, amount of remittance (taxes withheld in the month)", "amount": text(total), "records": n, "filter": f"/app/purchase-invoice?company={company}&docstatus=1&posting_date=%5B%22Between%22%2C%5B%22{start}%22%2C%22{end}%22%5D%5D"}]
    figures = {"remittance": text(total), "anyWithheld": "yes" if total else "no"}
    figures["_atc"] = {atc: text(v["tax"]) for atc, v in sorted(rows.items())}
    return {"figures": figures, "lines": lines, "warnings": warnings}


def compute(data: dict, ctx: Context) -> list[dict]:
    kind = wh.kinds(data)
    i14, i15 = dec(data.get("remittance")), dec(data.get("previouslyRemitted"))
    i16 = i14 - i15
    a, b, c = dec(data.get("surcharge")), dec(data.get("interest")), dec(data.get("compromise"))
    i17d = a + b + c
    i18 = i16 + i17d
    out = [
        wh.line("14", "Amount of Remittance", i14, kind("remittance")),
        wh.line("15", "Less: Amount Remitted from Previously Filed Form, if Amended", i15, kind("previouslyRemitted")),
        wh.line("16", "Net Amount of Remittance", i16, "derived"),
        wh.line("17A", "Surcharge", a, kind("surcharge")),
        wh.line("17B", "Interest", b, kind("interest")),
        wh.line("17C", "Compromise", c, kind("compromise")),
        wh.line("17D", "Total Penalties", i17d, "derived"),
        wh.line("18", "TOTAL AMOUNT OF REMITTANCE", i18, "derived"),
    ]
    for atc, tax in ((data.get("_atc") or {}) if isinstance(data.get("_atc"), dict) else {}).items():
        out.append(wh.line(f"ATC {atc}", f"Withheld under {atc}", dec(tax), "books"))
    out.append({"item": "_c", "label": "", "amount": centavos(0), "kind": "derived", "c": {"i16": i16, "i17d": i17d, "i18": i18}})
    return out


def needs(data: dict, ctx: Context) -> list[Need]:
    out = []
    if ctx.period.n % 3 == 0:
        out.append(draft_need(ctx.return_name, "period", "This is the third month of the quarter: the 0619-E is for months 1 and 2 only; the quarter is remitted on the 1601-EQ.", "The BIR does not take a 0619-E for a quarter's last month.", "text"))
    if not wh.s(data.get("signatoryName")):
        out.append(draft_need(ctx.return_name, "signatoryName", "Who signs the return (name, title, TIN)?", "The signature block prints the signatory.", "text"))
    return out


def print_rows(data: dict, comp: list[dict], ctx: Context) -> list[tuple[str, str]]:
    c = next(ln for ln in comp if ln["item"] == "_c")["c"]
    wh.refuse_first_negative(
        "0619-E",
        [
            ("Item 14", wh.neg(data.get("remittance"))),
            ("Item 15", wh.neg(data.get("previouslyRemitted"))),
            ("Item 16", c["i16"] < 0),
            ("Item 17A", wh.neg(data.get("surcharge"))),
            ("Item 17B", wh.neg(data.get("interest"))),
            ("Item 17C", wh.neg(data.get("compromise"))),
            ("Item 17D", c["i17d"] < 0),
            ("Item 18", c["i18"] < 0),
            *wh.payment_checks(data, (19, 20, 21, 22)),
        ],
    )
    w = wh.Writer("f0619E")
    w.put("month", f"{ctx.period.n:02d}{ctx.period.year}")
    w.put("dueDate", wh.slash_date(data.get("dueDate")) or wh.slash_date(due_date(ctx.period.end)))
    wh.yes_no(w, "amended", "yes" if ctx.is_amended else "no", True)
    wh.yes_no(w, "any", data.get("anyWithheld"), False)
    wh.common(w, data, ctx.company, ctx.contact_number)
    w.typed("i14", data.get("remittance"))
    w.typed("i15", data.get("previouslyRemitted"))
    w.computed("i16", c["i16"])
    w.typed("i17a", data.get("surcharge"))
    w.typed("i17b", data.get("interest"))
    w.typed("i17c", data.get("compromise"))
    w.computed("i17d", c["i17d"])
    w.computed("i18", c["i18"])
    wh.sign_and_pay(w, data, ctx.company)
    return w.out
