"""B35: offboarding export and deletion certificate.

`export_site(target)` writes, for the site it runs on, everything the client takes away:
- database and files backup (bench backup with files),
- the year-end pack of every company for every fiscal year with postings (CSV books,
  manifest, transmittal),
- the registration pack of every company,
- the full audit trail (PH Event Log) and print records as CSV,
- EXPORT-MANIFEST.json with SHA-256 of every file, and README.txt explaining the set.
Everything is produced from inside the site, so permissions and the BIR header are the same
as in the product. `ledger-site offboard <site>` calls it, then compresses the folder.

`deletion_certificate(...)` renders the text the provider signs after `ledger-site drop`.
"""

import csv
import hashlib
import io
import json
import os
import shutil

import frappe
from frappe.utils import now_datetime, nowdate

from ph_cas.audit.header import software_name, software_version


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(target: str, rel: str, content: bytes):
    p = os.path.join(target, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(content)
    return p


def _csv(doctype: str, fields: list[str], filters: dict | None = None) -> bytes:
    rows = frappe.get_all(doctype, filters=filters or {}, fields=fields, order_by="creation asc", limit_page_length=0)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(fields)
    for r in rows:
        w.writerow([r.get(f) for f in fields])
    return buf.getvalue().encode("utf-8")


def fiscal_years_with_postings(company: str) -> list[int]:
    years = frappe.db.sql(
        "select distinct year(posting_date) from `tabGL Entry` where company=%s and is_cancelled=0 order by 1", company
    )
    return [int(y[0]) for y in years if y[0]]


def export_site(target: str | None = None) -> dict:
    frappe.set_user("Administrator")
    target = target or frappe.get_site_path("private", "offboarding", now_datetime().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(target, exist_ok=True)
    produced = []

    # 1. database and files
    from frappe.utils.backups import new_backup

    b = new_backup(ignore_files=False, force=True)
    for attr in ("backup_path_db", "backup_path_files", "backup_path_private_files", "backup_path_conf"):
        p = getattr(b, attr, None)
        if p and os.path.exists(p):
            dest = os.path.join(target, "01_backup", os.path.basename(p))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(p, dest)
            produced.append(dest)

    # 2. books per company and year, 3. registration pack per company
    from ph_cas.books.yearend import build_pack
    from ph_cas.registration.pack import build as build_registration

    companies = frappe.get_all("Company", pluck="name")
    for company in companies:
        slug = frappe.scrub(company)
        for year in fiscal_years_with_postings(company):
            pack = build_pack(company, year)
            for name, content in pack["files"].items():
                produced.append(_write(target, f"02_books/{slug}/{year}/{name}", content))
        try:
            reg = build_registration(company)
            for name, content in reg["files"].items():
                produced.append(_write(target, f"03_registration/{slug}/{name}", content))
        except Exception:
            frappe.log_error("offboarding: registration pack", frappe.get_traceback())

    # 4. audit trail and print records
    produced.append(
        _write(
            target,
            "04_audit/event_log.csv",
            _csv("PH Event Log", ["name", "seq", "timestamp", "user", "event", "ref_doctype", "ref_name", "docstatus_after", "details", "previous_hash", "hash"]),
        )
    )
    produced.append(
        _write(
            target,
            "04_audit/print_records.csv",
            _csv("PH Print Record", ["name", "ref_doctype", "ref_name", "print_no", "printed_on", "printed_by", "method", "copy_type"]),
        )
    )
    for dt, fields in (
        ("Sales Invoice", ["name", "posting_date", "customer", "grand_total", "bir_serial", "docstatus"]),
        ("Purchase Invoice", ["name", "posting_date", "supplier", "grand_total", "docstatus"]),
        ("Payment Entry", ["name", "posting_date", "party_type", "party", "paid_amount", "bir_serial", "docstatus"]),
        ("Journal Entry", ["name", "posting_date", "total_debit", "docstatus"]),
    ):
        cols = [f for f in fields if f in ("name", "docstatus") or frappe.get_meta(dt).has_field(f)]
        produced.append(_write(target, f"05_registers/{frappe.scrub(dt)}.csv", _csv(dt, cols)))

    manifest = {
        "site": frappe.local.site,
        "exported_on": now_datetime().strftime("%Y-%m-%d %H:%M:%S"),
        "software": f"{software_name()} {software_version()}",
        "companies": companies,
        "files": {os.path.relpath(p, target): {"sha256": _sha(p), "bytes": os.path.getsize(p)} for p in produced},
    }
    _write(target, "EXPORT-MANIFEST.json", json.dumps(manifest, indent=1).encode("utf-8"))
    _write(target, "README.txt", readme(manifest).encode("utf-8"))
    return {"target": target, "files": len(produced), "manifest": manifest}


def readme(manifest: dict) -> str:
    return f"""Sentire Ledger offboarding export for {manifest["site"]}
Exported on {manifest["exported_on"]} by {manifest["software"]}

What is here
01_backup/        Complete database dump (.sql.gz) and the public and private files of the site.
                  Restorable on any Frappe bench of the same version (bench restore).
02_books/         For every company and every year with postings: the seven books as CSV with
                  the BIR header, MANIFEST.json with hashes, TRANSMITTAL.txt.
03_registration/  The registration pack of every company as last generated (Annex B answers,
                  sworn statement text, specimen prints, conformance report).
04_audit/         The complete hash-chained event log and the print records.
05_registers/     Registers of invoices, bills, payments and journal entries with BIR serials.
EXPORT-MANIFEST.json  SHA-256 and size of every file above. Verify a file with: sha256sum <file>

Retention: the books and the audit trail must be kept for ten years from the last entry of the
year they belong to. Keep this export in two places.
"""


def deletion_certificate(site: str, client: str, provider: str, deleted_on: str | None = None, export_accepted_on: str | None = None, signatory: str = "", position: str = "") -> str:
    deleted_on = deleted_on or nowdate()
    return f"""CERTIFICATE OF DELETION

{provider} certifies that the Sentire Ledger site

    {site}

operated for {client}, together with its database, uploaded files, encrypted backups held by the
provider, and the backup encryption key, was permanently deleted from the provider's systems on
{deleted_on}, after the client accepted the offboarding export on {export_accepted_on or "____________"}.

No copy of the client's accounting data remains with the provider, except the registration pack
and audit trail extracts the provider must keep for its own professional liability period, as set
out in the service agreement.

The licence to use the Sentire Ledger name and marks ended on the termination date. The client has
been reminded to notify its Revenue District Office of the change of accounting system or
provider.

Signed: ______________________________
{signatory}{", " + position if position else ""}
{provider}
Date: {deleted_on}
"""
