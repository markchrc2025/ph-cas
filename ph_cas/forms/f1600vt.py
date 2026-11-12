"""BIR Form 1600-VT, Monthly Remittance Return of Value-Added Tax Withheld
(January 2018 ENCS). Printed on the blank (map made in G2 from the blank's
geometry); centavos exact; five ATC rows; the MAP .DAT goes with it.

Data: rows [{atc, base, rate, withheld}] (books, from reverse-charge purchases),
previouslyRemitted (19), otherPayments (20), surcharge, interest, compromise
(23 to 25), amended, anyWithheld, category, relief, sheets, signatory and
payment inputs. Derived: 18, 21, 22, 26, 27.
"""

import frappe

from ph_cas.forms import withholding as wh
from ph_cas.forms.engine import Context
from ph_cas.forms.export import ExportRefusal
from ph_cas.forms.money import ZERO, centavos, dec, text
from ph_cas.forms.needs import Need, draft_need

ROWS_ON_THE_FORM = 5
INPUTS = [
    ("previouslyRemitted", "19 Taxes remitted in return previously filed (amended)", "money"),
    ("otherPayments", "20 Other payments made", "money"),
    ("surcharge", "23 Surcharge", "money"),
    ("interest", "24 Interest", "money"),
    ("compromise", "25 Compromise", "money"),
    ("reliefYesNo", "12 Availing of tax relief (yes or no)", "select:yes,no"),
    ("reliefSpecify", "12A specify", "text"),
    ("sheetsAttached", "4 Number of sheets attached", "text"),
] + wh.HEAD_INPUTS + wh.PAY_INPUTS
SCHEDULES = {"rows": ("VAT withheld by ATC (5 rows on the paper)", ["ATC", "Tax base", "Rate %", "Tax withheld"], ["atc", "base", "rate", "withheld"])}


def feed(ctx: Context) -> dict:
    company = ctx.company["name"]
    start, end = ctx.period.start, ctx.period.end
    found = frappe.db.sql(
        """select ph_rc_atc as atc, coalesce(sum(ph_rc_base), 0) as base, coalesce(sum(ph_rc_vat), 0) as vat, count(*) as n
           from `tabPurchase Invoice` where company = %s and docstatus = 1 and posting_date between %s and %s
             and ifnull(ph_rc_atc, '') != '' group by ph_rc_atc order by ph_rc_atc""",
        (company, start, end),
        as_dict=True,
    )
    rows, total, n = [], ZERO, 0
    for r in found:
        base, vat = centavos(r.base), centavos(r.vat)
        rate = (vat / base * 100).quantize(dec("0.01")) if base else ZERO
        rows.append({"atc": r.atc, "base": text(base), "rate": text(rate), "withheld": text(vat)})
        total += vat
        n += int(r.n)
    warnings = []
    if len(rows) > ROWS_ON_THE_FORM:
        warnings.append(f"The month has {len(rows)} ATCs; the paper has room for {ROWS_ON_THE_FORM}.")
    figures = {"rows": rows, "anyWithheld": "yes" if total else "no"}
    lines = [{"key": "rows", "label": "VAT withheld by ATC (reverse charge)", "amount": text(total), "records": n, "filter": f"/app/purchase-invoice?company={company}&docstatus=1&posting_date=%5B%22Between%22%2C%5B%22{start}%22%2C%22{end}%22%5D%5D"}]
    return {"figures": figures, "lines": lines, "warnings": warnings}


def _rows(data: dict) -> list[dict]:
    return data.get("rows") if isinstance(data.get("rows"), list) else []


def compute(data: dict, ctx: Context) -> list[dict]:
    kind = wh.kinds(data)
    out = []
    i18 = ZERO
    for i, r in enumerate(_rows(data), start=1):
        w = centavos(r.get("withheld"))
        i18 += w
        out.append(wh.line(f"{12 + i} base", f"Row {i}: tax base ({wh.s(r.get('atc')) or 'no ATC'})", dec(r.get("base")), kind("rows")))
        out.append(wh.line(f"{12 + i} tax", f"Row {i}: VAT withheld ({wh.s(r.get('atc')) or 'no ATC'})", w, kind("rows")))
    i19, i20 = dec(data.get("previouslyRemitted")), dec(data.get("otherPayments"))
    i21 = i19 + i20
    i22 = i18 - i21
    i23, i24, i25 = (dec(data.get(k)) for k in ("surcharge", "interest", "compromise"))
    i26 = i23 + i24 + i25
    i27 = i22 + i26
    out += [
        wh.line("18", "Total Taxes Withheld", i18, "derived"),
        wh.line("19", "Less: Taxes Remitted in Return Previously Filed, if Amended", i19, kind("previouslyRemitted")),
        wh.line("20", "Other Payments Made", i20, kind("otherPayments")),
        wh.line("21", "Total Tax Payments Made", i21, "derived"),
        wh.line("22", "Tax Still Due/(Overremittance)", i22, "derived"),
        wh.line("23", "Surcharge", i23, kind("surcharge")),
        wh.line("24", "Interest", i24, kind("interest")),
        wh.line("25", "Compromise", i25, kind("compromise")),
        wh.line("26", "Total Penalties", i26, "derived"),
        wh.line("27", "TOTAL AMOUNT STILL DUE/(Overremittance)", i27, "derived"),
        {"item": "_c", "label": "", "amount": ZERO, "kind": "derived", "c": {"i18": i18, "i21": i21, "i22": i22, "i26": i26, "i27": i27}},
    ]
    return out


def needs(data: dict, ctx: Context) -> list[Need]:
    out = []
    live = [r for r in _rows(data) if wh.s(r.get("atc")) or dec(r.get("withheld")) != 0]
    if len(live) > ROWS_ON_THE_FORM:
        out.append(draft_need(ctx.return_name, "rows", f"The month has {len(live)} ATC rows; the paper has room for {ROWS_ON_THE_FORM}. Which rows are combined or removed?", "The form cannot carry more rows.", "text"))
    for i, r in enumerate(live, start=1):
        if not wh.s(r.get("atc")):
            out.append(draft_need(ctx.return_name, f"rows.{i}.atc", f"Row {i} has an amount but no ATC. Which ATC is it?", "The paper prints the ATC per row.", "atc"))
    if not wh.s(data.get("signatoryName")):
        out.append(draft_need(ctx.return_name, "signatoryName", "Who signs the return (name, title, TIN)?", "The signature block prints the signatory.", "text"))
    return out


def print_rows(data: dict, comp: list[dict], ctx: Context) -> list[tuple[str, str]]:
    c = next(ln for ln in comp if ln["item"] == "_c")["c"]
    rows = _rows(data)
    live = [r for r in rows if wh.s(r.get("atc")) or dec(r.get("withheld")) != 0]
    if len(live) > ROWS_ON_THE_FORM:
        raise ExportRefusal(f"The 1600-VT has {len(live)} ATC rows; the paper has room for {ROWS_ON_THE_FORM}. Combine or remove rows, then print again.")
    used = rows[:ROWS_ON_THE_FORM]
    checks = [(f"Item {12 + i}", wh.neg(r.get("base")) or wh.neg(r.get("withheld"))) for i, r in enumerate(used, start=1)]
    checks += [("Item 18", c["i18"] < 0), ("Item 19", wh.neg(data.get("previouslyRemitted"))), ("Item 20", wh.neg(data.get("otherPayments"))), ("Item 22", c["i22"] < 0), ("Item 23", wh.neg(data.get("surcharge"))), ("Item 24", wh.neg(data.get("interest"))), ("Item 25", wh.neg(data.get("compromise"))), ("Item 27", c["i27"] < 0), *wh.payment_checks(data, (28, 29, 30, 31))]
    wh.refuse_first_negative("1600-VT", checks)
    w = wh.Writer("f1600VT")
    w.put("month", f"{ctx.period.n:02d}")
    w.put("year", str(ctx.period.year))
    wh.yes_no(w, "amended", "yes" if ctx.is_amended else "no", True)
    wh.yes_no(w, "any", data.get("anyWithheld"), False)
    w.put("sheets", wh.digits(data.get("sheetsAttached")))
    wh.common(w, data, ctx.company, ctx.contact_number)
    wh.yes_no(w, "relief", data.get("reliefYesNo"), False)
    w.put("reliefSpecify", data.get("reliefSpecify"))
    for i, r in enumerate(used, start=1):
        if not any(wh.s(r.get(k)) for k in ("atc", "base", "rate", "withheld")):
            continue
        w.put(f"r{i}Atc", r.get("atc"))
        w.typed(f"r{i}Base", r.get("base"))
        rate = dec(r.get("rate"))
        w.put(f"r{i}Rate", str(int(rate)) if rate == int(rate) else wh.s(r.get("rate")))
        w.typed(f"r{i}Withheld", r.get("withheld"))
    w.computed("i18", c["i18"])
    w.typed("i19", data.get("previouslyRemitted"))
    w.typed("i20", data.get("otherPayments"))
    w.computed("i21", c["i21"])
    w.computed("i22", c["i22"])
    w.typed("i23", data.get("surcharge"))
    w.typed("i24", data.get("interest"))
    w.typed("i25", data.get("compromise"))
    w.computed("i26", c["i26"])
    w.computed("i27", c["i27"])
    wh.sign_and_pay(w, data, ctx.company)
    w.put("p2Tin", wh.tin14(ctx.company.get("tax_id"), ctx.company.get("ph_branch_code")))
    w.put("p2Name", wh.full_name(ctx.company))
    return w.out


def write_attachment(return_doc) -> str:
    """The MAP .DAT (monthly alphalist of payees) for the month."""
    from ph_cas.dat.qap import generate

    name = generate(return_doc.company, "1600VT", str(return_doc.period_start), str(return_doc.period_end))
    return_doc.db_set("alphalist_file", name)
    return name


def on_filed(return_doc):
    write_attachment(return_doc)
