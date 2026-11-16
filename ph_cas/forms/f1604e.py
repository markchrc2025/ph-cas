"""BIR Form 1604-E, Annual Information Return of Creditable Income Taxes Withheld,
Expanded (January 2018 ENCS). Printed on the blank (map made in G2); the annual
alphalist of payees .DAT goes with it, built from the four 1601-EQ returns of the
year (filed snapshots when they exist, the books otherwise).

Data: sch1 rows (one per quarter: date, bank, number, withheld, penalties,
total; books from the filed 1601-EQ returns), sch2 rows (1606 remittances,
typed), amended, sheets, top withholding agent, signatory inputs.
"""

import frappe

from ph_cas.forms import withholding as wh
from ph_cas.forms.engine import Context
from ph_cas.forms.money import ZERO, centavos, dec, text
from ph_cas.forms.needs import Need, draft_need

INPUTS = [
    ("topAgent", "8A Top withholding agent (yes or no)", "select:yes,no"),
    ("sheetsAttached", "3 Number of sheets attached", "text"),
    ("category", "8 Category of withholding agent", "select:private,government"),
    ("email", "10 Email address (blank: the company's)", "text"),
    ("signatoryName", "Signatory: name", "text"),
    ("signatoryTitle", "Signatory: title", "text"),
    ("signatoryTin", "Signatory: TIN", "text"),
    ("taxAgentNo", "Tax agent accreditation number", "text"),
    ("taxAgentIssueDate", "Tax agent date of issue (yyyy-mm-dd)", "text"),
    ("taxAgentExpiryDate", "Tax agent expiry (yyyy-mm-dd)", "text"),
]
SCHEDULES = {
    "sch1": ("Schedule 1: remittances per 1601-EQ (one row per quarter)", ["Quarter", "Date (yyyy-mm-dd)", "Bank or agency", "Number", "Taxes withheld", "Penalties", "Total remitted"], ["q", "date", "bank", "number", "withheld", "penalties", "total"]),
    "sch2": ("Schedule 2: remittances per 1606 (one row per month)", ["Month (1 to 12)", "Date (yyyy-mm-dd)", "Bank or agency", "Number", "Taxes withheld", "Penalties", "Total remitted"], ["m", "date", "bank", "number", "withheld", "penalties", "total"]),
}


def feed(ctx: Context) -> dict:
    company = ctx.company["name"]
    year = ctx.period.year
    rows, lines, total = [], [], ZERO
    for q in range(1, 5):
        r = frappe.db.get_value("PH Tax Return", {"company": company, "form": "1601-EQ", "period_key": f"{year}-Q{q}", "docstatus": 1}, ["name", "filed_on", "filed_reference"], as_dict=True)
        if not r:
            continue
        withheld = dec(frappe.db.get_value("PH Tax Return Line", {"parent": r.name, "item": "19"}, "amount") or 0)
        penalties = dec(frappe.db.get_value("PH Tax Return Line", {"parent": r.name, "item": "30"}, "amount") or 0)
        remitted = dec(frappe.db.get_value("PH Tax Return Line", {"parent": r.name, "item": "31"}, "amount") or 0)
        rows.append({"q": str(q), "date": str(r.filed_on or ""), "bank": "", "number": wh.s(r.filed_reference)[:20], "withheld": text(centavos(withheld)), "penalties": text(centavos(penalties)), "total": text(centavos(remitted))})
        total += centavos(withheld)
        lines.append({"key": f"sch1.q{q}", "label": f"Schedule 1, quarter {q} from {r.name}", "amount": text(centavos(withheld)), "records": 1, "filter": f"/app/ph-tax-return/{r.name}"})
    warnings = [] if len(rows) == 4 else [f"Only {len(rows)} of the year's four 1601-EQ returns are filed in the Ledger; the missing quarters are typed."]
    top = "yes" if frappe.get_cached_value("Company", company, "ph_top_withholding_agent") else "no"  # Item 8A, from the Company
    return {"figures": {"sch1": rows, "topAgent": top}, "lines": lines, "warnings": warnings}


def _rows(data, key):
    return data.get(key) if isinstance(data.get(key), list) else []


def compute(data: dict, ctx: Context) -> list[dict]:
    kind = wh.kinds(data)
    out = []
    totals = {}
    for key, label in (("sch1", "Schedule 1 (1601-EQ)"), ("sch2", "Schedule 2 (1606)")):
        w = p = t = ZERO
        for r in _rows(data, key):
            w += centavos(r.get("withheld"))
            p += centavos(r.get("penalties"))
            t += centavos(r.get("total"))
        totals[key] = (w, p, t)
        out.append(wh.line(f"{key} withheld", f"{label}: taxes withheld", w, kind(key)))
        out.append(wh.line(f"{key} penalties", f"{label}: penalties", p, kind(key)))
        out.append(wh.line(f"{key} total", f"{label}: total remitted", t, kind(key)))
    out.append({"item": "_c", "label": "", "amount": ZERO, "kind": "derived", "c": totals})
    return out


def needs(data: dict, ctx: Context) -> list[Need]:
    out = []
    if (data.get("category") or "private") == "private" and (data.get("topAgent") or "") not in ("yes", "no"):
        out.append(draft_need(ctx.return_name, "topAgent", "Is the company a top withholding agent?", "Item 8A marks yes or no.", "choice", ["yes", "no"]))
    if not wh.s(data.get("signatoryName")):
        out.append(draft_need(ctx.return_name, "signatoryName", "Who signs the return (name, title, TIN)?", "The signature block prints the signatory.", "text"))
    return out


def print_rows(data: dict, comp: list[dict], ctx: Context) -> list[tuple[str, str]]:
    c = next(ln for ln in comp if ln["item"] == "_c")["c"]
    w = wh.Writer("f1604E")
    w.put("year", str(ctx.period.year))
    wh.yes_no(w, "amended", "yes" if ctx.is_amended else "no", True)
    w.put("sheets", wh.digits(data.get("sheetsAttached")))
    wh.common(w, data, ctx.company, ctx.contact_number)
    if (data.get("category") or "private") == "private":
        wh.yes_no(w, "top", data.get("topAgent"), False)
    for r in _rows(data, "sch1"):
        q = wh.digits(r.get("q"))[:1]
        if q not in "1234" or not q:
            continue
        p = f"s1q{q}"
        w.put(f"{p}Date", wh.slash_date(r.get("date")))
        w.put(f"{p}Bank", r.get("bank"))
        w.put(f"{p}Number", r.get("number"))
        w.typed(f"{p}Withheld", r.get("withheld"))
        w.typed(f"{p}Penalties", r.get("penalties"))
        w.typed(f"{p}Total", r.get("total"))
    for r in _rows(data, "sch2"):
        m = wh.digits(r.get("m"))
        if not m or not 1 <= int(m) <= 12:
            continue
        p = f"s2m{int(m)}"
        w.put(f"{p}Date", wh.slash_date(r.get("date")))
        w.put(f"{p}Bank", r.get("bank"))
        w.put(f"{p}Number", r.get("number"))
        w.typed(f"{p}Withheld", r.get("withheld"))
        w.typed(f"{p}Penalties", r.get("penalties"))
        w.typed(f"{p}Total", r.get("total"))
    for key, p in (("sch1", "s1Total"), ("sch2", "s2Total")):
        wd, pe, to = c[key]
        if wd or pe or to:
            w.computed(f"{p}Withheld", wd)
            w.computed(f"{p}Penalties", pe)
            w.computed(f"{p}Total", to)
    side = "Ind" if (ctx.company.get("ph_taxpayer_type") or "") == "Individual" else "Non"
    w.put(f"sig{side}Name", data.get("signatoryName"))
    w.put(f"sig{side}TitleTin", wh.title_tin_line(data.get("signatoryTitle"), data.get("signatoryTin")))
    w.put("agentNo", data.get("taxAgentNo"))
    w.put("agentIssue", wh.slash_date(data.get("taxAgentIssueDate")))
    w.put("agentExpiry", wh.slash_date(data.get("taxAgentExpiryDate")))
    w.put("p2Tin", wh.tin14(ctx.company.get("tax_id"), ctx.company.get("ph_branch_code")))
    w.put("p2Name", wh.full_name(ctx.company))
    return w.out


def write_attachment(return_doc) -> str:
    """The annual alphalist of payees .DAT (1604-E layout) for the year."""
    from ph_cas.dat.qap import generate

    name = generate(return_doc.company, "1604E", str(return_doc.period_start), str(return_doc.period_end))
    return_doc.db_set("alphalist_file", name)  # None when there is no payee (no file)
    return name


def on_filed(return_doc):
    write_attachment(return_doc)
