"""B25: the year-end e-books pack.

RR 16-2006 fixes no single column order: the files may be text, CSV, DAT or DBF
with a file layout description (field name, type, width, decimals). RMO 9-2021
V (books of accounts) 2: soft copies within 30 days after the close of the
taxable year, on a USB drive or other storage device labelled with the taxpayer's
name and the taxable year, with a transmittal letter listing each file's name,
type and size. So the pack writes each book as CSV with the Annex B header,
FILE-LAYOUT.txt, the transmittal and a manifest of SHA-256 hashes. The writer is pluggable: when
the record format arrives, a writer registered in FORMAT_WRITERS replaces the
CSV writer for that book without changing the pack.
"""

import hashlib
import io
import json
import zipfile

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from ph_cas.audit.export import csv_with_header
from ph_cas.audit.header import ph_header_lines

BOOKS = [
    ("General Journal", "ph_cas.ph_cas.report.ph_general_journal.ph_general_journal.execute", "GJ"),
    ("General Ledger", "ph_cas.ph_cas.report.ph_general_ledger_book.ph_general_ledger_book.execute", "GL"),
    ("Cash Receipts Book", "ph_cas.ph_cas.report.ph_cash_receipts_book.ph_cash_receipts_book.execute", "CRB"),
    ("Cash Disbursements Book", "ph_cas.ph_cas.report.ph_cash_disbursements_book.ph_cash_disbursements_book.execute", "CDB"),
    ("Sales Journal", "ph_cas.ph_cas.report.ph_sales_journal.ph_sales_journal.execute", "SJ"),
    ("Purchase Journal", "ph_cas.ph_cas.report.ph_purchase_journal.ph_purchase_journal.execute", "PJ"),
    ("Inventory Book", "ph_cas.ph_cas.report.ph_inventory_book.ph_inventory_book.execute", "INV"),
]

# book code -> callable(company, start, end, columns, rows) -> (filename, bytes). Empty until RR 16-2006 arrives.
FORMAT_WRITERS: dict = {}


def _rows_as_lists(columns, rows):
    keys = [c["fieldname"] for c in columns]
    return [c["label"] for c in columns], [[r.get(k) for k in keys] for r in rows]


_TYPES = {"Currency": ("Numeric", 2), "Float": ("Numeric", 2), "Int": ("Numeric", 0), "Percent": ("Numeric", 2),
          "Date": ("Date (YYYY-MM-DD)", 0), "Datetime": ("Date and time", 0)}


def file_layout(company: str, year: int, books: list) -> str:
    """The file layout description RR 16-2006 asks for: every field's name, type,
    width and decimals, per file. books: [(file name, title, columns, rows)]."""
    header_lines = len(ph_header_lines(company))
    lines = [
        f"FILE LAYOUT DESCRIPTION, COMPUTERIZED BOOKS OF ACCOUNTS, TAXABLE YEAR {year} (RR 16-2006)",
        "",
        "Every file: comma-separated text (CSV), UTF-8, CRLF line ends, text in double quotes when it holds a comma.",
        f"Lines 1 to {header_lines}: the Annex B header (taxpayer, address, TIN, software). Line {header_lines + 1}: blank.",
        f"Line {header_lines + 2}: the column names below. Then one line per record.",
        "Numbers: no thousands separator, a leading minus sign for negatives, decimals as stated.",
        "",
    ]
    for name, title, columns, rows in books:
        lines += [f"{name}  ({title}, {len(rows)} records)", f"  {'No.':<4}{'Field':<34}{'Type':<20}{'Width':>6}{'Decimals':>10}"]
        for i, c in enumerate(columns, 1):
            kind, decimals = _TYPES.get(c.get("fieldtype"), ("Character", 0))
            width = max([len(str(c.get("label") or ""))] + [len(str(r.get(c["fieldname"]) if r.get(c["fieldname"]) is not None else "")) for r in rows])
            lines.append(f"  {i:<4}{str(c.get('label') or c['fieldname'])[:33]:<34}{kind:<20}{width:>6}{decimals:>10}")
        lines.append("")
    return "\r\n".join(lines) + "\r\n"


def build_pack(company: str, year: int) -> dict:
    start, end = f"{year}-01-01", f"{year}-12-31"
    tin = (frappe.get_cached_value("Company", company, "tax_id") or "000-000-000").replace("-", "")
    branch = frappe.get_cached_value("Company", company, "ph_branch_code") or "00000"
    files, layout = {}, []
    for title, path, code in BOOKS:
        fn = frappe.get_attr(path)
        filters = {"company": company, "from_date": start, "to_date": end}
        columns, rows = fn(filters)
        labels, data = _rows_as_lists(columns, rows)
        if code in FORMAT_WRITERS:
            name, content = FORMAT_WRITERS[code](company, start, end, columns, rows)
        else:
            name, content = f"{tin}{branch}_{year}_{code}.csv", csv_with_header(labels, data, company)
        files[name] = content
        layout.append((name, title, columns, rows))
    files["FILE-LAYOUT.txt"] = file_layout(company, year, layout).encode("utf-8")
    manifest = {
        "company": company, "tin": tin, "branch": branch, "year": year,
        "generated_on": now_datetime().strftime("%Y-%m-%d %H:%M:%S"), "generated_by": frappe.session.user,
        "format": "CSV with the Annex B header and a file layout description (RR 16-2006)",
        "files": {name: {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)} for name, content in files.items()},
    }
    files["MANIFEST.json"] = json.dumps(manifest, indent=1).encode("utf-8")
    files["TRANSMITTAL.txt"] = transmittal(company, year, manifest).encode("utf-8")
    return {"files": files, "manifest": manifest}


def transmittal(company: str, year: int, manifest: dict) -> str:
    header = ph_header_lines(company)
    lines = [
        "TRANSMITTAL OF COMPUTERIZED BOOKS OF ACCOUNTS (RMO 9-2021)",
        "",
        f"Taxpayer: {header[0]}",
        f"Address: {header[1]}",
        header[2],
        f"Taxable year: {year}",
        f"Submitted within 30 days after year-end to the RDO (due {year + 1}-01-30).",
        f"USB label: {header[0]}, taxable year {year}",
        "",
        "Files on the USB (name, type, size):",
    ]
    for name, meta in manifest["files"].items():
        kind = "Text (file layout description)" if name == "FILE-LAYOUT.txt" else "CSV (comma-separated text)"
        lines.append(f"  {name}  {kind}  {meta['bytes']} bytes  SHA-256 {meta['sha256']}")
    lines += [
        "",
        "Software and version: " + header[3].replace("Software: ", ""),
        f"Generated on {manifest['generated_on']} by {manifest['generated_by']}.",
        "",
        "ORUS QR stamp: [attach the QR stamp from ORUS after online registration of the books]",
        "",
        "I certify that the books on this medium are complete and were generated by the registered CAS.",
        "",
        "______________________________",
        "Signature over printed name, designation, TIN",
    ]
    return "\r\n".join(lines) + "\r\n"


@frappe.whitelist()
def download_pack(company: str, year: int):
    frappe.has_permission("Company", "read", company, throw=True)
    out = build_pack(company, int(year))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in out["files"].items():
            z.writestr(name, content)
    frappe.response["type"] = "binary"
    frappe.response["filename"] = f"ebooks_{year}_{company}.zip".replace(" ", "_")
    frappe.response["filecontent"] = buf.getvalue()
    from ph_cas.audit.events import record

    record("export", "Company", company, 0, {"year_end_ebooks": int(year), "files": list(out["files"].keys())})


def verify_pack(files: dict) -> dict:
    """Read a pack back: every hash in the manifest matches its file."""
    manifest = json.loads(files["MANIFEST.json"].decode("utf-8"))
    bad = [n for n, m in manifest["files"].items() if hashlib.sha256(files.get(n, b"")).hexdigest() != m["sha256"]]
    return {"ok": not bad, "bad": bad, "year": manifest["year"]}
