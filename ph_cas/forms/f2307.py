"""BIR Form 2307, Certificate of Creditable Tax Withheld at Source (January 2018
ENCS), printed on page 1 of the blank. A certificate is one PH 2307 Issued
record (payor = the company, payee = the supplier, Part III blocks A and B); the
2307 return for a quarter is the run that prints every certificate issued for
it into one PDF. Centavos exact, pesos and centavos in one cell as typed.
"""

import io

import frappe
from pypdf import PdfReader, PdfWriter

from ph_cas.birpdf import BirPdfError, render_return
from ph_cas.forms import withholding as wh
from ph_cas.forms.engine import Context
from ph_cas.forms.export import ExportRefusal
from ph_cas.forms.money import ZERO, centavos, dec, text
from ph_cas.forms.needs import Need, draft_need

BLOCK_ROWS = 10
QUARTER_BOUNDS = {1: ("01/01", "03/31"), 2: ("04/01", "06/30"), 3: ("07/01", "09/30"), 4: ("10/01", "12/31")}
INPUTS = [
    ("payorSignatoryName", "Payor signatory: name", "text"),
    ("payorSignatoryTitle", "Payor signatory: title", "text"),
    ("payorSignatoryTin", "Payor signatory: TIN", "text"),
    ("payorTaxAgentNo", "Payor tax agent accreditation number", "text"),
    ("payorTaxAgentIssued", "Payor tax agent date of issue (yyyy-mm-dd)", "text"),
    ("payorTaxAgentExpiry", "Payor tax agent expiry (yyyy-mm-dd)", "text"),
]
SCHEDULES = {}


def _mmddyyyy(v) -> str:
    t = wh.s(v)
    m = __import__("re").fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t)
    return m.group(2) + m.group(3) + m.group(1) if m else wh.digits(t)[:8]


def _cert_rows(cert, c: dict, data: dict, qn: int, year: int) -> list[tuple[str, str]]:
    """The c2307:* rows for one PH 2307 Issued record."""
    out: list[tuple[str, str]] = []

    def put(k, v):
        t = wh.s(v)
        if t != "":
            out.append((f"c2307:{k}", t))

    q_from, q_to = QUARTER_BOUNDS[qn]
    put("periodFrom", _mmddyyyy(f"{year}-{q_from[:2]}-{q_from[3:]}"))
    put("periodTo", _mmddyyyy(f"{year}-{q_to[:2]}-{q_to[3:]}"))
    payee14 = wh.tin14(cert.payee_tin, "")
    put("payeeTin1", payee14[0:3])
    put("payeeTin2", payee14[3:6])
    put("payeeTin3", payee14[6:9])
    put("payeeBranch", payee14[9:14])
    put("payeeName", cert.payee_name)
    put("payeeAddress", cert.payee_address)
    put("payeeZip", cert.payee_zip)
    name = wh.full_name(c)
    if not name:
        raise ExportRefusal("Complete the company's registered name (or last and first name for an individual) before printing this certificate.")
    payor14 = wh.tin14(c.get("tax_id"), c.get("ph_branch_code"))
    put("payorTin1", payor14[0:3])
    put("payorTin2", payor14[3:6])
    put("payorTin3", payor14[6:9])
    put("payorBranch", payor14[9:14])
    put("payorName", name)
    put("payorAddress", " ".join((c.get("ph_registered_address") or "").split()))
    put("payorZip", c.get("ph_zip"))
    for prefix in ("a", "b"):
        rows = [ln for ln in cert.lines if (ln.block or "A").upper() == prefix.upper()]
        if len(rows) > BLOCK_ROWS:
            raise ExportRefusal(f"Certificate {cert.name} has {len(rows)} rows in Part III block {prefix.upper()}; the form has room for {BLOCK_ROWS}.")
        t1 = t2 = t3 = ti = tt = ZERO
        any_amount = False
        for i, ln in enumerate(rows, start=1):
            put(f"{prefix}{i}Desc", ln.description)
            put(f"{prefix}{i}Atc", ln.atc)
            m1, m2, m3, tax = (centavos(getattr(ln, k)) for k in ("month_1", "month_2", "month_3", "tax_withheld"))
            total = m1 + m2 + m3
            has = any(x != 0 for x in (m1, m2, m3, tax))
            if m1:
                put(f"{prefix}{i}M1", text(m1))
            if m2:
                put(f"{prefix}{i}M2", text(m2))
            if m3:
                put(f"{prefix}{i}M3", text(m3))
            if tax or has:
                put(f"{prefix}{i}Tax", text(tax))
            if has:
                put(f"{prefix}{i}Total", text(total))
                any_amount = True
            t1, t2, t3, ti, tt = t1 + m1, t2 + m2, t3 + m3, ti + total, tt + tax
        if any_amount:
            put(f"{prefix}TotalM1", text(t1))
            put(f"{prefix}TotalM2", text(t2))
            put(f"{prefix}TotalM3", text(t3))
            put(f"{prefix}TotalIncome", text(ti))
            put(f"{prefix}TotalTax", text(tt))
    put("payorSigName", wh.s(data.get("payorSignatoryName")) or name)
    put("payorSigTitleTin", wh.title_tin_line(data.get("payorSignatoryTitle"), wh.s(data.get("payorSignatoryTin")) or c.get("tax_id")))
    put("payorAgentNo", data.get("payorTaxAgentNo"))
    put("payorAgentIssued", _mmddyyyy(data.get("payorTaxAgentIssued")))
    put("payorAgentExpiry", _mmddyyyy(data.get("payorTaxAgentExpiry")))
    return out


def certificates(company: str, start, end) -> list[str]:
    return frappe.get_all("PH 2307 Issued", {"company": company, "docstatus": 1, "period_from": [">=", start], "period_to": ["<=", end]}, pluck="name", order_by="supplier, period_from")


def feed(ctx: Context) -> dict:
    company = ctx.company["name"]
    names = certificates(company, ctx.period.start, ctx.period.end)
    total = sum((centavos(frappe.db.get_value("PH 2307 Issued", n, "total_tax")) for n in names), ZERO)
    figures = {"certificates": names}
    lines = [{"key": "certificates", "label": "Certificates issued for the quarter", "amount": text(total), "records": len(names), "filter": f"/app/ph-2307-issued?company={company}&docstatus=1"}]
    return {"figures": figures, "lines": lines, "warnings": [] if names else ["No 2307 issued for the quarter yet; issue them from PH 2307 Issued."]}


def compute(data: dict, ctx: Context) -> list[dict]:
    names = data.get("certificates") if isinstance(data.get("certificates"), list) else []
    out = []
    total = ZERO
    for n in names:
        v = frappe.db.get_value("PH 2307 Issued", n, ["payee_name", "total_tax"], as_dict=True)
        if not v:
            continue
        tax = centavos(v.total_tax)
        total += tax
        out.append(wh.line(n, f"Certificate to {v.payee_name}", tax, "books"))
    out.append(wh.line("total", "Total tax withheld certified for the quarter", total, "derived"))
    return out


def needs(data: dict, ctx: Context) -> list[Need]:
    out = []
    if not wh.full_name(ctx.company):
        out.append(draft_need(ctx.return_name, "payor", "What is the company's registered name?", "The certificate prints the payor's name.", "text"))
    return out


def print_rows(data: dict, comp: list[dict], ctx: Context) -> list[tuple[str, str]]:
    """The first certificate's rows (the engine prints one blank per rows list; the run
    uses print_all for every certificate)."""
    names = data.get("certificates") if isinstance(data.get("certificates"), list) else []
    if not names:
        raise ExportRefusal("No certificate to print for the quarter.")
    cert = frappe.get_doc("PH 2307 Issued", names[0])
    return _cert_rows(cert, ctx.company, data, ctx.period.quarter_no, ctx.period.year)


def certificate_pdf(cert, c: dict, data: dict, qn: int, year: int, watermark=None, printed_at=None) -> bytes:
    rows = _cert_rows(cert, c, data, qn, year)
    return render_return("2307", "2018-01", rows, watermark, printed_at)


def print_all(data: dict, ctx: Context, watermark=None, printed_at=None) -> bytes:
    """Every certificate of the quarter, one page each, in one PDF."""
    names = data.get("certificates") if isinstance(data.get("certificates"), list) else []
    if not names:
        raise ExportRefusal("No certificate to print for the quarter.")
    writer = PdfWriter()
    for n in names:
        cert = frappe.get_doc("PH 2307 Issued", n)
        try:
            pdf = certificate_pdf(cert, ctx.company, data, ctx.period.quarter_no, ctx.period.year, watermark, printed_at)
        except BirPdfError as e:
            raise ExportRefusal(f"{n}: {e}") from None
        for page in PdfReader(io.BytesIO(pdf)).pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.add_metadata({"/Title": f"BIR Form 2307, {len(names)} certificates", "/Creator": "Sentire Ledger", "/Producer": "Sentire Ledger birpdf"})
    writer.write(out)
    return out.getvalue()
