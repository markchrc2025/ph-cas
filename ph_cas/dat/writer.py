"""B27: the DAT framework. Every BIR alphalist file is comma-delimited with
CRLF line ends, amounts with two decimals and no thousands separator, text
fields quoted or not as each layout says (docs/reference/bir-dat-sample-layouts.md).

A layout is a list of record specs; each spec is a list of (field, kind):
  q  quoted text        u  unquoted text       n  amount, 2 decimals
  i  integer            p  period MM/YYYY      d  date MM/DD/YYYY
  e  empty field (no quotes)                   qe quoted empty ("") when blank, quoted otherwise
  qn quoted, or an empty field with no quotes when blank (RELIEF detail rows)
  nz amount, 2 decimals, but a bare 0 when zero (RELIEF detail rows)

Verification status per layout is kept in docs/dat/VERIFICATION.md: since B62 every
alphalist layout (QAP, 1604-E, MAP, SAWT) matches the BIR Alphalist module 7.4 byte
for byte, and the RELIEF files match RELIEF 2.3 (B47).
"""

import re

import frappe
from frappe import _
from frappe.utils import flt, getdate

CRLF = "\r\n"


def fmt(value, kind: str) -> str:
    if kind == "q":
        return '"' + str(value if value is not None else "").replace('"', "") + '"'
    if kind == "qe":
        s = str(value if value is not None else "")
        return '"' + s.replace('"', "") + '"' if s else '""'
    if kind == "u":
        return str(value if value is not None else "").replace(",", " ").replace('"', "")
    if kind == "qn":
        s = str(value if value is not None else "").replace('"', "")
        return f'"{s}"' if s else ""
    if kind == "n":
        return f"{flt(value):.2f}"
    if kind == "nz":
        v = round(flt(value), 2)
        return "0" if v == 0 else f"{v:.2f}"
    if kind == "i":
        return str(int(value or 0))
    if kind == "p":
        d = getdate(value)
        return f"{d.month:02d}/{d.year}"
    if kind == "d":
        d = getdate(value)
        return f"{d.month:02d}/{d.day:02d}/{d.year}"
    if kind == "e":
        return ""
    raise ValueError(kind)


def record(values: list, kinds: list) -> str:
    assert len(values) == len(kinds), (values, kinds)
    return ",".join(fmt(v, k) for v, k in zip(values, kinds))


def file_bytes(lines: list[str], trailing_crlf: bool = True) -> bytes:
    body = CRLF.join(lines)
    if trailing_crlf:
        body += CRLF
    return body.encode("ascii", errors="replace")


def clean_name(text) -> str:
    """A name as the BIR Alphalist Validation module 7.4 accepts it. Its validator rejects
    ' & , and Ñ in a name ("Invalid character on field Registered Name", run on 16 Nov
    2026) and accepts . - / ( ) # and digits. So: upper case, & becomes AND, Ñ becomes N
    (accents dropped), apostrophes and quotes go, a comma becomes a space, single spaces."""
    import unicodedata

    t = str(text or "").upper().replace("&", " AND ")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"['\"`]", "", t).replace(",", " ")
    return re.sub(r"\s+", " ", t).strip()


def tin9(tin: str) -> str:
    digits = re.sub(r"\D", "", tin or "")
    if len(digits) != 9:
        frappe.throw(_("TIN {0} is not 9 digits; the DAT file needs a 9-digit TIN.").format(tin))
    return digits


def branch4(branch: str) -> str:
    """The DAT branch code: 4 digits, as the BIR Alphalist module 7.4 writes and validates it."""
    from ph_cas.setup.master_data import dat_branch

    return dat_branch(branch or "00000")


def file_name(tin: str, branch: str, period_end, form_code: str, kind: str = "alphalist") -> str:
    """TIN9 + BC4 + MMYYYY + FORM.DAT (RMC 15-2025 Annex B); annual files use
    12312026 style dates; RELIEF files are TIN9 + S/P/I + MMYYYY.DAT (B29)."""
    d = getdate(period_end)
    if kind == "annual":
        return f"{tin9(tin)}{branch4(branch)}{d.month:02d}{d.day:02d}{d.year}{form_code}.DAT"
    return f"{tin9(tin)}{branch4(branch)}{d.month:02d}{d.year}{form_code}.DAT"


def agent(company: str) -> dict:
    c = frappe.get_cached_doc("Company", company)
    individual = (c.get("ph_taxpayer_type") or "Non-individual") == "Individual"
    return {
        "tin": tin9(c.get("tax_id")),
        "branch": branch4(c.get("ph_branch_code")),
        "name": clean_name(c.get("ph_registered_name") or c.company_name),
        "rdo": c.get("ph_rdo") or "",
        "individual": individual,
        # an individual files under his own name (the SAWT header's last, first and middle name)
        **{k: (clean_name(c.get(f"ph_{k}_name")) if individual else "") for k in ("last", "first", "middle")},
    }


def party_fields(party_type: str, party: str) -> dict:
    from ph_cas.setup.master_data import payee_name_parts

    d = frappe.get_cached_doc(party_type, party)
    parts = payee_name_parts(party_type, party)
    tin = d.get("ph_tin") or d.get("tax_id") or ""
    return {"tin": tin9(tin), "branch": branch4(d.get("ph_branch_code")), **{k: clean_name(v) for k, v in parts.items()}}


def store(company: str, form_code: str, period_start, period_end, filename: str, content: bytes, layout_status: str, rows: int) -> str:
    """Keep the generated file as a PH Alphalist File record with its hash and attachment."""
    import hashlib

    doc = frappe.get_doc({
        "doctype": "PH Alphalist File", "company": company, "form_code": form_code, "period_start": period_start, "period_end": period_end,
        "file_name": filename, "sha256": hashlib.sha256(content).hexdigest(), "rows": rows, "layout_status": layout_status,
    })
    doc.insert(ignore_permissions=True)
    f = frappe.get_doc({"doctype": "File", "file_name": filename, "attached_to_doctype": "PH Alphalist File", "attached_to_name": doc.name, "content": content, "is_private": 1})
    f.insert(ignore_permissions=True)
    doc.db_set("file_url", f.file_url)
    from ph_cas.audit.events import record as log

    log("export", "PH Alphalist File", doc.name, 0, {"file": filename, "sha256": doc.sha256, "rows": rows})
    return doc.name
