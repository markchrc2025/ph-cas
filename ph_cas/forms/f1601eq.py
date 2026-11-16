"""BIR Form 1601-EQ, Quarterly Remittance Return of Creditable Income Taxes
Withheld, Expanded (January 2019 ENCS). Printed on the blank; centavos exact;
six ATC rows on the paper; the QAP .DAT goes with it.

Data: rows [{atc, base, rate, withheld}] (books, one row per ATC), remittance1 and
remittance2 (20, 21, item 14 of the filed 0619-E of each month; nothing when none was filed), previouslyRemitted (22),
overRemittancePrior (23, books), otherPayments (24), surcharge, interest,
compromise (27 to 29), overRemittanceChoice (refunded, tcc, carried), amended,
anyWithheld, category, sheetsAttached, signatory and payment inputs.
Derived: 19, 25, 26, 30, 31. The filed snapshot carries the alphalist rows
(payee by ATC) the QAP is written from.
"""

import frappe
from frappe.utils import add_months, get_first_day, get_last_day

from ph_cas.forms import withholding as wh
from ph_cas.forms.engine import Context
from ph_cas.forms.money import ZERO, centavos, dec, text
from ph_cas.forms.needs import Need, draft_need

ROWS_ON_THE_FORM = 6
CHOICES = ("refunded", "tcc", "carried")
INPUTS = [
    ("previouslyRemitted", "22 Remittances made in previously filed return (amended)", "money"),
    ("otherPayments", "24 Other payments made", "money"),
    ("surcharge", "27 Surcharge", "money"),
    ("interest", "28 Interest", "money"),
    ("compromise", "29 Compromise", "money"),
    ("overRemittanceChoice", "Over-remittance: refunded, tcc or carried", "select:refunded,tcc,carried"),
    ("sheetsAttached", "Number of sheets attached", "text"),
] + wh.HEAD_INPUTS + wh.PAY_INPUTS
SCHEDULES = {"rows": ("Taxes withheld by ATC (6 rows on the paper)", ["ATC", "Tax base", "Rate %", "Tax withheld"], ["atc", "base", "rate", "withheld"])}


def feed(ctx: Context) -> dict:
    company = ctx.company["name"]
    start, end = ctx.period.start, ctx.period.end
    atc_rows = wh.ewt_rows(company, start, end)
    rows = []
    for atc, v in sorted(atc_rows.items()):
        base, tax = centavos(v["base"]), centavos(v["tax"])
        rate = (tax / base * 100).quantize(dec("0.01")) if base else ZERO
        rows.append({"atc": atc, "base": text(base), "rate": text(rate), "withheld": text(tax)})
    m1s, m1e = get_first_day(start), get_last_day(start)
    m2s, m2e = get_first_day(add_months(start, 1)), get_last_day(add_months(start, 1))
    (m1, m1_return), (m2, m2_return) = wh.remitted_0619e(company, m1s), wh.remitted_0619e(company, m2s)
    prev = frappe.db.get_value("PH Tax Return", {"company": company, "form": "1601-EQ", "docstatus": 1, "period_end": ["<", start]}, ["name", "period_end"], order_by="period_end desc", as_dict=True)
    carry = ZERO
    if prev and ctx.period.quarter_no != 1 and prev.period_end.year == start.year:
        i26 = frappe.db.get_value("PH Tax Return Line", {"parent": prev.name, "item": "26"}, "amount") or 0
        carry = centavos(-dec(i26)) if dec(i26) < 0 else ZERO
    total = sum((centavos(v["tax"]) for v in atc_rows.values()), ZERO)
    warnings = []
    for label, (ms, me), paid, ret in (("Item 20", (m1s, m1e), m1, m1_return), ("Item 21", (m2s, m2e), m2, m2_return)):
        withheld = wh.ewt_total(company, ms, me)
        month = ms.strftime("%B %Y")
        if not ret and withheld:
            warnings.append(f"{label}: no filed 0619-E for {month}, so nothing is credited as remitted; the books show {text(withheld)} withheld that month, which this return now carries as still due.")
        elif ret and paid != withheld:
            warnings.append(f"{label}: the filed 0619-E for {month} remitted {text(paid)}; the books show {text(withheld)} withheld that month.")
    if len(rows) > ROWS_ON_THE_FORM:
        warnings.append(f"The quarter has {len(rows)} ATCs; the paper has room for {ROWS_ON_THE_FORM}. Combine rows or attach a schedule.")
    pi = f"/app/purchase-invoice?company={company}&docstatus=1&posting_date=%5B%22Between%22%2C%5B%22{start}%22%2C%22{end}%22%5D%5D"
    figures = {"rows": rows, "remittance1": text(m1), "remittance2": text(m2), "overRemittancePrior": text(carry), "anyWithheld": "yes" if total else "no"}
    lines = [
        {"key": "rows", "label": "Taxes withheld by ATC for the quarter", "amount": text(total), "records": len(rows), "filter": pi},
        {"key": "remittance1", "label": "Item 20, remitted in month 1 (filed 0619-E)", "amount": text(m1), "records": 1 if m1_return else 0, "filter": f"/app/ph-tax-return/{m1_return}" if m1_return else f"/app/ph-tax-return?form=0619-E&company={company}"},
        {"key": "remittance2", "label": "Item 21, remitted in month 2 (filed 0619-E)", "amount": text(m2), "records": 1 if m2_return else 0, "filter": f"/app/ph-tax-return/{m2_return}" if m2_return else f"/app/ph-tax-return?form=0619-E&company={company}"},
        {"key": "overRemittancePrior", "label": "Item 23, over-remittance from the previous quarter of the year", "amount": text(carry), "records": 1 if prev else 0, "filter": f"/app/ph-tax-return/{prev.name}" if prev else ""},
    ]
    return {"figures": figures, "lines": lines, "warnings": warnings}


def _rows(data: dict) -> list[dict]:
    return data.get("rows") if isinstance(data.get("rows"), list) else []


def compute(data: dict, ctx: Context) -> list[dict]:
    kind = wh.kinds(data)
    rows = _rows(data)
    out = []
    i19 = ZERO
    for i, r in enumerate(rows, start=1):
        w = centavos(r.get("withheld"))
        i19 += w
        item = 12 + i
        out.append(wh.line(f"{item} base", f"Row {i}: tax base ({wh.s(r.get('atc')) or 'no ATC'})", dec(r.get("base")), kind("rows")))
        out.append(wh.line(f"{item} tax", f"Row {i}: tax withheld ({wh.s(r.get('atc')) or 'no ATC'})", w, kind("rows")))
    i20, i21, i22, i23, i24 = (dec(data.get(k)) for k in ("remittance1", "remittance2", "previouslyRemitted", "overRemittancePrior", "otherPayments"))
    i25 = i20 + i21 + i22 + i23 + i24
    i26 = i19 - i25
    i27, i28, i29 = (dec(data.get(k)) for k in ("surcharge", "interest", "compromise"))
    i30 = i27 + i28 + i29
    i31 = i26 + i30
    over = i31 < 0
    picked = wh.s(data.get("overRemittanceChoice")).lower()
    choice = picked if over and picked in CHOICES and not (picked == "carried" and ctx.period.quarter_no == 4) else ""
    out += [
        wh.line("19", "Total Taxes Withheld for the Quarter", i19, "derived"),
        wh.line("20", "Less: Remittances Made, 1st Month of the Quarter", i20, kind("remittance1")),
        wh.line("21", "Remittances Made, 2nd Month of the Quarter", i21, kind("remittance2")),
        wh.line("22", "Remittances Made in Previously Filed Return, if Amended", i22, kind("previouslyRemitted")),
        wh.line("23", "Over-remittance from Previous Quarter of the Same Taxable Year", i23, kind("overRemittancePrior")),
        wh.line("24", "Other Payments Made", i24, kind("otherPayments")),
        wh.line("25", "Total Remittances Made", i25, "derived"),
        wh.line("26", "Tax Still Due/(Over-remittance)", i26, "derived"),
        wh.line("27", "Surcharge", i27, kind("surcharge")),
        wh.line("28", "Interest", i28, kind("interest")),
        wh.line("29", "Compromise", i29, kind("compromise")),
        wh.line("30", "Total Penalties", i30, "derived"),
        wh.line("31", "TOTAL AMOUNT STILL DUE/(Over-remittance)", i31, "derived"),
        {"item": "_c", "label": "", "amount": ZERO, "kind": "derived", "c": {"i19": i19, "i25": i25, "i26": i26, "i30": i30, "i31": i31, "over": over, "choice": choice}},
    ]
    return out


def needs(data: dict, ctx: Context) -> list[Need]:
    out = []
    rows = _rows(data)
    live = [r for r in rows if wh.s(r.get("atc")) or dec(r.get("base")) != 0 or dec(r.get("withheld")) != 0]
    if len(live) > ROWS_ON_THE_FORM:
        out.append(draft_need(ctx.return_name, "rows", f"The quarter has {len(live)} ATC rows; the paper has room for {ROWS_ON_THE_FORM}. Which rows are combined or removed?", "The form cannot carry more rows.", "text"))
    for i, r in enumerate(live, start=1):
        if not wh.s(r.get("atc")):
            out.append(draft_need(ctx.return_name, f"rows.{i}.atc", f"Row {i} has an amount but no ATC. Which ATC is it?", "The paper prints the ATC per row.", "atc"))
    c = next(ln for ln in compute(data, ctx) if ln["item"] == "_c")["c"]
    if c["over"] and not c["choice"]:
        out.append(draft_need(ctx.return_name, "overRemittanceChoice", wh.OVER_REMITTANCE_CHOICE_MISSING + (" (not carried over: this is the fourth quarter)" if ctx.period.quarter_no == 4 else ""), "Item 26 is an over-remittance; one box is marked.", "choice", list(CHOICES)))
    if not wh.s(data.get("signatoryName")):
        out.append(draft_need(ctx.return_name, "signatoryName", "Who signs the return (name, title, TIN)?", "The signature block prints the signatory.", "text"))
    return out


def _rate_text(v) -> str:
    t = wh.s(v).rstrip("%").strip()
    return f"{t}%" if t else ""


def print_rows(data: dict, comp: list[dict], ctx: Context) -> list[tuple[str, str]]:
    from ph_cas.forms.export import ExportRefusal

    c = next(ln for ln in comp if ln["item"] == "_c")["c"]
    rows = _rows(data)
    live = [r for r in rows if wh.s(r.get("atc")) or dec(r.get("base")) != 0 or dec(r.get("withheld")) != 0]
    if len(live) > ROWS_ON_THE_FORM:
        raise ExportRefusal(f"The 1601-EQ has {len(live)} ATC rows; the paper has room for {ROWS_ON_THE_FORM}. Combine or remove rows, then print again.")
    used = rows[:ROWS_ON_THE_FORM]
    checks = [(f"Item {13 + i}", wh.neg(r.get("base")) or wh.neg(r.get("withheld"))) for i, r in enumerate(used)]
    checks += [
        ("Item 19", c["i19"] < 0),
        ("Item 20", wh.neg(data.get("remittance1"))),
        ("Item 21", wh.neg(data.get("remittance2"))),
        ("Item 22", wh.neg(data.get("previouslyRemitted"))),
        ("Item 23", wh.neg(data.get("overRemittancePrior"))),
        ("Item 24", wh.neg(data.get("otherPayments"))),
        ("Item 25", c["i25"] < 0),
        ("Item 27", wh.neg(data.get("surcharge"))),
        ("Item 28", wh.neg(data.get("interest"))),
        ("Item 29", wh.neg(data.get("compromise"))),
        ("Item 30", c["i30"] < 0),
        *wh.payment_checks(data, (32, 33, 34, 35)),
    ]
    wh.refuse_first_negative("1601-EQ", checks)
    if c["over"] and not c["choice"]:
        raise ExportRefusal(wh.OVER_REMITTANCE_CHOICE_MISSING)
    w = wh.Writer("f1601EQ")
    w.put("year", str(ctx.period.year))
    w.put(f"q{ctx.period.quarter_no}", "true")
    wh.yes_no(w, "amended", "yes" if ctx.is_amended else "no", True)
    wh.yes_no(w, "any", data.get("anyWithheld"), False)
    w.put("sheets", wh.digits(data.get("sheetsAttached")))
    wh.common(w, data, ctx.company, ctx.contact_number)
    w.put("p2Tin", wh.tin14(ctx.company.get("tax_id"), ctx.company.get("ph_branch_code")))
    w.put("p2Name", wh.full_name(ctx.company))
    for i, r in enumerate(used, start=1):
        if not any(wh.s(r.get(k)) for k in ("atc", "base", "rate", "withheld")):
            continue
        w.put(f"r{i}Atc", r.get("atc"))
        w.typed(f"r{i}Base", r.get("base"))
        w.put(f"r{i}Rate", _rate_text(r.get("rate")))
        w.typed(f"r{i}Withheld", r.get("withheld"))
    w.computed("i19", c["i19"])
    w.typed("i20", data.get("remittance1"))
    w.typed("i21", data.get("remittance2"))
    w.typed("i22", data.get("previouslyRemitted"))
    w.typed("i23", data.get("overRemittancePrior"))
    w.typed("i24", data.get("otherPayments"))
    w.computed("i25", c["i25"])
    w.computed("i26", abs(c["i26"]))
    w.typed("i27", data.get("surcharge"))
    w.typed("i28", data.get("interest"))
    w.typed("i29", data.get("compromise"))
    w.computed("i30", c["i30"])
    w.computed("i31", abs(c["i31"]))
    if c["over"]:
        w.put({"refunded": "overRefunded", "tcc": "overTcc", "carried": "overCarried"}[c["choice"]], "true")
    wh.sign_and_pay(w, data, ctx.company)
    return w.out


def filed_snapshot_extra(data: dict, ctx: Context) -> dict:
    """The alphalist model the QAP is written from: payee rows by ATC as at filing."""
    from ph_cas.dat.qap import _not_withheld, _withheld

    company = ctx.company["name"]
    return {"alphalist": {"withheld": _withheld(company, ctx.period.start, ctx.period.end), "not_withheld": _not_withheld(company, ctx.period.start, ctx.period.end)}}


def write_attachment(return_doc) -> str:
    """The QAP .DAT for a 1601-EQ return (from the posted records; the snapshot holds the
    same rows once filed), stored as a PH Alphalist File and linked to the return."""
    from ph_cas.dat.qap import generate

    name = generate(return_doc.company, "1601EQ", str(return_doc.period_start), str(return_doc.period_end))
    return_doc.db_set("alphalist_file", name)
    return name


def on_filed(return_doc):
    write_attachment(return_doc)
