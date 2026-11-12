"""Shared pieces of the withholding forms (0619-E, 1601-EQ, 1601-C, 1600-VT, 2307):
printed on the blank from the draft (no eBIRForms file), centavos exact, no minus
sign anywhere on the paper. Ported from the Portal's withholding-print.ts."""

import re
from decimal import Decimal

from ph_cas.forms.export import ExportRefusal, tin_parts
from ph_cas.forms.money import ZERO, centavos, dec

OVER_REMITTANCE_CHOICE_MISSING = "Choose what to do with the over-remittance: to be refunded, to be issued a Tax Credit Certificate, or to be carried over."

PAY_INPUTS = [
    ("signatoryName", "Signatory: name", "text"),
    ("signatoryTitle", "Signatory: title or designation", "text"),
    ("signatoryTin", "Signatory: TIN", "text"),
    ("taxAgentNo", "Tax agent accreditation number", "text"),
    ("taxAgentIssueDate", "Tax agent date of issue (yyyy-mm-dd)", "text"),
    ("taxAgentExpiryDate", "Tax agent expiry date (yyyy-mm-dd)", "text"),
    ("payCashBank", "Cash/bank debit memo: bank", "text"),
    ("payCashNumber", "Cash/bank debit memo: number", "text"),
    ("payCashDate", "Cash/bank debit memo: date (yyyy-mm-dd)", "text"),
    ("payCashAmount", "Cash/bank debit memo: amount", "money"),
    ("payCheckBank", "Check: bank", "text"),
    ("payCheckNumber", "Check: number", "text"),
    ("payCheckDate", "Check: date (yyyy-mm-dd)", "text"),
    ("payCheckAmount", "Check: amount", "money"),
    ("payTaxDebitNumber", "Tax debit memo: number", "text"),
    ("payTaxDebitDate", "Tax debit memo: date (yyyy-mm-dd)", "text"),
    ("payTaxDebitAmount", "Tax debit memo: amount", "money"),
    ("payOthersSpecify", "Others: specify", "text"),
    ("payOthersBank", "Others: bank or agency", "text"),
    ("payOthersNumber", "Others: number", "text"),
    ("payOthersDate", "Others: date (yyyy-mm-dd)", "text"),
    ("payOthersAmount", "Others: amount", "money"),
]
HEAD_INPUTS = [
    ("anyWithheld", "Any taxes withheld? (yes or no)", "select:yes,no"),
    ("category", "Category of withholding agent", "select:private,government"),
    ("email", "Email address on the return (blank: the company's)", "text"),
]


def s(v) -> str:
    return v.strip() if isinstance(v, str) else ("" if v is None else str(v))


def digits(v) -> str:
    return re.sub(r"\D", "", s(v))


def plain(d) -> str:
    """"1234.50": centavos exact, a minus kept (the caller refuses negatives first)."""
    c = centavos(d)
    return f"{c:.2f}"


def slash_date(v) -> str:
    """yyyy-mm-dd typed as the forms want it, mm/dd/yyyy; anything else as typed."""
    t = s(v)
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t)
    return f"{m.group(2)}/{m.group(3)}/{m.group(1)}" if m else t


def full_name(c: dict) -> str:
    if (c.get("ph_taxpayer_type") or "") == "Individual":
        given = " ".join(x for x in (c.get("ph_first_name"), c.get("ph_middle_name")) if x)
        return ", ".join(x for x in (c.get("ph_last_name"), given) if x)
    return c.get("ph_registered_name") or c.get("company_name") or ""


def format_tin(tin) -> str:
    d = digits(tin)
    return "-".join(g for g in (d[0:3], d[3:6], d[6:9], d[9:]) if g)


def tin14(tin, branch=None) -> str:
    d = digits(tin)
    if len(d) < 9:
        return d
    given = d[9:14] or digits(branch)
    return d[:9] + (given.rjust(5, "0") if given else "")


def title_tin_line(title, tin) -> str:
    t, n = s(title), format_tin(tin)
    return " / ".join(x for x in (t, f"TIN {n}" if n else "") if x)


class Writer:
    def __init__(self, ns: str):
        self.ns = ns
        self.out: list[tuple[str, str]] = []

    def put(self, k: str, v):
        t = s(v)
        if t != "":
            self.out.append((f"{self.ns}:{k}", t))

    def typed(self, k: str, v):
        self.put(k, s(v))

    def computed(self, k: str, d):
        self.put(k, plain(d))


def common(w: Writer, data: dict, c: dict, contact: str):
    t = tin_parts(c.get("tax_id") or "", c.get("ph_branch_code") or "00000")
    w.put("tin1", t["t1"])
    w.put("tin2", t["t2"])
    w.put("tin3", t["t3"])
    w.put("branch", t["branch5"])
    w.put("rdo", c.get("ph_rdo"))
    w.put("name", full_name(c))
    w.put("address", " ".join((c.get("ph_registered_address") or "").split()))
    w.put("zip", c.get("ph_zip"))
    w.put("contact", s(data.get("contact")) or contact or c.get("ph_contact_number"))
    w.put("email", s(data.get("email")) or c.get("ph_email"))
    cat = s(data.get("category")).lower() or ("government" if (c.get("ph_taxpayer_class") or "") == "Government" else "private")
    if cat == "private":
        w.put("catPrivate", "true")
    if cat == "government":
        w.put("catGovernment", "true")


def yes_no(w: Writer, base: str, v, no_by_default: bool):
    t = s(v).lower()
    if t == "yes":
        w.put(f"{base}Yes", "true")
    elif t == "no" or (no_by_default and t != "yes"):
        w.put(f"{base}No", "true")


def sign_and_pay(w: Writer, data: dict, c: dict):
    side = "Ind" if (c.get("ph_taxpayer_type") or "") == "Individual" else "Non"
    w.put(f"sig{side}Name", data.get("signatoryName"))
    w.put(f"sig{side}TitleTin", title_tin_line(data.get("signatoryTitle"), data.get("signatoryTin")))
    w.put("agentNo", data.get("taxAgentNo"))
    w.put("agentIssue", slash_date(data.get("taxAgentIssueDate")))
    w.put("agentExpiry", slash_date(data.get("taxAgentExpiryDate")))
    for row, key in (("payCash", "cash"), ("payCheck", "check")):
        w.put(f"{key}Bank", data.get(f"{row}Bank"))
        w.put(f"{key}Number", data.get(f"{row}Number"))
        w.put(f"{key}Date", slash_date(data.get(f"{row}Date")))
        w.typed(f"{key}Amount", data.get(f"{row}Amount"))
    w.put("debitNumber", data.get("payTaxDebitNumber"))
    w.put("debitDate", slash_date(data.get("payTaxDebitDate")))
    w.typed("debitAmount", data.get("payTaxDebitAmount"))
    w.put("othersSpecify", data.get("payOthersSpecify"))
    w.put("othersBank", data.get("payOthersBank"))
    w.put("othersNumber", data.get("payOthersNumber"))
    w.put("othersDate", slash_date(data.get("payOthersDate")))
    w.typed("othersAmount", data.get("payOthersAmount"))


def neg(v) -> bool:
    return dec(v) < 0


def refuse_first_negative(paper: str, checks: list[tuple[str, bool]]):
    for where, is_neg in checks:
        if is_neg:
            raise ExportRefusal(f"A negative amount cannot be printed on the {paper} yet: the BIR blank has no place for a minus sign. {where} is negative.")


def payment_checks(data: dict, items: tuple[int, int, int, int]) -> list[tuple[str, bool]]:
    return [
        (f"Item {items[0]}", neg(data.get("payCashAmount"))),
        (f"Item {items[1]}", neg(data.get("payCheckAmount"))),
        (f"Item {items[2]}", neg(data.get("payTaxDebitAmount"))),
        (f"Item {items[3]}", neg(data.get("payOthersAmount"))),
    ]


def line(item: str, label: str, amount: Decimal, kind: str) -> dict:
    return {"item": item, "label": label, "amount": centavos(amount), "kind": kind}


def kinds(data: dict):
    books = (data.get("_source") or {}).get("books") or {}

    def kind(key: str) -> str:
        return "books" if key in books and data.get(key) == books[key] else "typed"

    return kind


def ewt_rows(company: str, start, end) -> dict:
    from ph_cas.tax.returns import _ewt_rows

    return _ewt_rows(company, start, end)


def ewt_total(company: str, start, end) -> Decimal:
    return sum((centavos(v["tax"]) for v in ewt_rows(company, start, end).values()), ZERO)
