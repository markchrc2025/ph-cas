"""B30: the registration pack for a client's CAS application (RMO 9-2021,
RMC 5-2021). Everything comes from the site itself:

- Annex C-1 (system description) drafted from Company and PH CAS Settings;
- sample prints: the latest issued invoice, credit note, collection receipt
  and 2307, and each book for the current month;
- the audit-trail printout for the last 30 days and the chain check;
- the Annex B answers with remarks, read from docs/CONFORMANCE.md: only items
  marked built or verified are answered YES; everything else goes in a gaps list;
- the joint sworn statement prefilled with the provider (the firm) and the client;
- the client's notice to its RDO that the provider keeps its records as a third-party
  custodian (RR 9-2009 Sec. 6.3.1; RDO answer 3 in docs/DECISIONS.md);
- the conformance report for the pinned versions.
"""

import io
import json
import os
import re
import zipfile

import frappe
from frappe import _
from frappe.utils import add_days, get_first_day, get_last_day, now_datetime, nowdate

import ph_cas
from ph_cas.audit.header import company_facts, ph_header_lines, platform_version, software_name, software_version


def conformance_rows() -> list[dict]:
    path = os.path.join(os.path.dirname(ph_cas.__file__), "..", "docs", "CONFORMANCE.md")
    rows = []
    if not os.path.exists(path):
        return rows
    for line in open(path, encoding="utf-8"):
        if not line.startswith("| ") or line.startswith("| Item") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        item, req, status, bundle, evidence = cells[:5]
        answer = "YES" if status.lower().startswith(("built", "verified")) else "NO"
        rows.append({"item": item, "requirement": req, "status": status, "answer": answer, "bundle": bundle, "evidence": evidence})
    return rows


def _settings():
    return frappe.get_single("PH CAS Settings")


def annex_c1(company: str) -> str:
    c = frappe.get_cached_doc("Company", company)
    f = company_facts(company)
    s = _settings()
    return "\r\n".join([
        "ANNEX C-1: SYSTEM DESCRIPTION (RMC 5-2021)",
        "",
        f"Taxpayer: {f['name']}",
        f"TIN: {f['tin']}-{f['branch']}  RDO: {c.get('ph_rdo') or ''}",
        f"Address: {f['address']}",
        f"VAT status: {c.get('ph_vat_status') or ''}  Taxpayer classification: {c.get('ph_taxpayer_class') or ''}",
        "",
        f"System: {software_name()} version {platform_version()}",
        "Type: Computerized Accounting System (CAS) with electronic invoicing capability, hosted by the provider in the Philippines, one site per taxpayer.",
        f"Software provider: {s.get('provider_name') or '(set in PH CAS Settings)'}  TIN {s.get('provider_tin') or ''}",
        "",
        "Modules: general ledger with general journal, sales and purchase journals, cash receipts and cash disbursements books, inventory book; sales invoicing (sales invoice, credit note, debit note, collection receipt) with BIR serial numbering per branch and document type; purchases with input VAT and expanded withholding; withholding certificates (2307) and alphalist files (QAP, SAWT, MAP, 1604-E, RELIEF); period-end figures for 2550Q, 2551Q, 0619-E, 1601-EQ, 1600-VT and the income tax returns; compliance calendar; year-end e-books pack.",
        "",
        "Controls: posted documents cannot be deleted, edited in their accounting fields, reposted or renumbered; drafts cannot be printed; documents carry the posting day; closed periods block postings for every role; every print after the first is marked REPRINT; a hash-chained event log records every create, submit, cancel, print, export, sign-in and settings change, verified daily; one session per user, password expiry, two-factor sign-in and deactivation after failed sign-ins.",
        "",
        "Books generated: General Journal, General Ledger, Cash Receipts Book, Cash Disbursements Book, Sales Journal, Purchase Journal, Inventory Book, each with totals and tie-out to the ledger, printed with the taxpayer's name, address, TIN-branch, software name and version, user and date-time.",
        "",
        "Backups: daily encrypted backups of the database and files, kept ten years, restore drill monthly (see the hosting runbook).",
        "",
        f"Prepared on {now_datetime().strftime('%Y-%m-%d %H:%M')} by {frappe.session.user}.",
    ]) + "\r\n"


def annex_b_answers(company: str) -> tuple[str, list[dict]]:
    rows = conformance_rows()
    gaps = [r for r in rows if r["answer"] == "NO"]
    lines = ["ANNEX B (RMC 5-2021): FUNCTIONAL AND TECHNICAL REQUIREMENTS, ANSWERS WITH REMARKS", ""]
    for r in rows:
        lines.append(f"Item {r['item']}: {r['answer']}")
        lines.append(f"  Requirement: {r['requirement']}")
        lines.append(f"  Remarks: {r['status']}; evidence: {r['evidence'] or 'see conformance report'}")
    lines += ["", f"Items answered NO ({len(gaps)}): " + (", ".join(g["item"] for g in gaps) if gaps else "none")]
    return "\r\n".join(lines) + "\r\n", gaps


def joint_sworn_statement(company: str) -> str:
    f = company_facts(company)
    s = _settings()
    return "\r\n".join([
        "JOINT SWORN STATEMENT (RMC 5-2021 Annex E / RMO 9-2021)",
        "",
        f"We, {s.get('provider_signatory') or '[PROVIDER SIGNATORY]'}, {s.get('provider_signatory_position') or '[position]'} of {s.get('provider_name') or '[PROVIDER]'} (TIN {s.get('provider_tin') or '[TIN]'}), the software provider,",
        f"and [CLIENT SIGNATORY, position] of {f['name']} (TIN {f['tin']}-{f['branch']}), the taxpayer-user,",
        "after having been duly sworn in accordance with law, hereby depose and state:",
        "",
        f"1. The taxpayer uses {software_name()} version {platform_version()} as its Computerized Accounting System, hosted by the provider in the Philippines.",
        "2. The system has no facility that may suppress, delete or alter sales and other transactions once posted, nor renumber or reuse document serials; corrections are made only through credit and debit notes and adjusting entries that are themselves recorded.",
        "3. The system generates the books of accounts, invoices and reports described in Annex C-1 in accordance with the requirements of Annex B, and keeps an audit trail of all transactions and activities.",
        "4. Any major enhancement to the system shall be the subject of a new application, and any minor enhancement shall be reported in writing to the RDO.",
        "5. Upon termination of the service agreement between the provider and the taxpayer, the taxpayer shall inform the RDO and the registration shall be cancelled accordingly.",
        "6. Backups of the database are kept for ten (10) years and are available to the BIR upon request.",
        "",
        "IN WITNESS WHEREOF, we have hereunto set our hands this ____ day of __________, 20__, at ____________.",
        "",
        f"______________________________          ______________________________",
        f"{s.get('provider_signatory') or '[Provider signatory]'}                   [Client signatory]",
        f"TIN {s.get('provider_signatory_tin') or ''}                              TIN",
        "",
        "SUBSCRIBED AND SWORN to before me this ____ day of __________, 20__, affiants exhibiting their government-issued IDs.",
    ]) + "\r\n"


def custody_notice(company: str) -> str:
    """The client tells its RDO, before its records go to the provider, who keeps them and where
    (RR 9-2009 Sec. 6.3.1). Records and backups stay in the Philippines (Secs. 6.2.1 to 6.2.3)."""
    c = frappe.get_cached_doc("Company", company)
    f = company_facts(company)
    s = _settings()
    provider = s.get("provider_name") or "[PROVIDER]"
    where = (s.get("records_location") or "[DATA CENTRE AND BACKUP SITE IN THE PHILIPPINES, set in PH CAS Settings]").replace("\n", ", ")
    return "\r\n".join([
        "NOTICE OF THIRD-PARTY CUSTODY OF BOOKS OF ACCOUNTS AND RECORDS",
        "(Revenue Regulations No. 9-2009, Section 6.3.1)",
        "",
        "Date: ____________________",
        "",
        "The Revenue District Officer",
        f"Revenue District Office No. {c.get('ph_rdo') or '___'}",
        "",
        "Sir or Madam:",
        "",
        f"{f['name']}, TIN {f['tin']}-{f['branch']}, of {f['address'] or '[registered address]'}, gives notice that beginning ____________________ its books of accounts, invoices and the records that support them are kept in electronic form by a third party:",
        "",
        f"Custodian: {provider}, TIN {s.get('provider_tin') or '[TIN]'}",
        f"Custodian's address: {(s.get('provider_address') or '[address]').replace(chr(10), ', ')}",
        f"System: {software_name()} version {platform_version()}, a computerized accounting system hosted by the custodian, one site and one database for this taxpayer",
        f"Where the records and backups are kept: {where}",
        "",
        "The records and their backups are kept in the Philippines for ten (10) years. The taxpayer can view and print them at any time, and will produce them, in print or electronic form, at its registered address or wherever the BIR directs.",
        "",
        "The taxpayer remains responsible for its books and records. The custodian keeps them on the taxpayer's behalf under their service agreement; when the agreement ends, the custodian delivers a complete copy to the taxpayer and the taxpayer will inform this office.",
        "",
        "Respectfully,",
        "",
        "______________________________",
        "[Name and position of the taxpayer's authorized signatory]",
        f"{f['name']}",
        "",
        "Conforme:",
        "",
        "______________________________",
        f"{s.get('provider_signatory') or '[Provider signatory]'}, {s.get('provider_signatory_position') or '[position]'}",
        f"{provider}, custodian",
    ]) + "\r\n"


def conformance_report() -> str:
    try:
        erp = frappe.get_attr("erpnext.__version__")
    except Exception:
        erp = "?"
    rows = conformance_rows()
    yes = sum(1 for r in rows if r["answer"] == "YES")
    lines = [
        "CONFORMANCE REPORT",
        f"ph_cas {ph_cas.__version__} on ERPNext {erp}, Frappe {frappe.__version__}",
        f"Annex B items answered YES: {yes} of {len(rows)}",
        "",
    ] + [f"{r['item']}: {r['answer']} ({r['status']})" for r in rows]
    return "\r\n".join(lines) + "\r\n"


def _render(doctype, name, fmt) -> str | None:
    if not name:
        return None
    doc = frappe.get_doc(doctype, name)
    frappe.flags.ph_in_print_preview = True  # a specimen for the pack, not an issued print
    try:
        pf = frappe.get_doc("Print Format", fmt)
        return frappe.render_template(pf.html, {"doc": doc, "frappe": frappe})
    finally:
        frappe.flags.ph_in_print_preview = False


def _bir_2307(name) -> bytes | None:
    """The issued certificate on the BIR's own 2307 blank, as Print on BIR form gives it."""
    if not name:
        return None
    from ph_cas.forms import f2307
    from ph_cas.forms.engine import taxpayer_block

    cert = frappe.get_doc("PH 2307 Issued", name)
    c = taxpayer_block(frappe.get_cached_doc("Company", cert.company))
    return f2307.certificate_pdf(cert, c, {}, (cert.period_from.month - 1) // 3 + 1, cert.period_from.year)


def _latest(doctype, filters):
    rows = frappe.get_all(doctype, filters={"docstatus": 1, **filters}, fields=["name"], order_by="creation desc", limit=1)
    return rows[0].name if rows else None


def _report_html(title, module, filters) -> str:
    cols, rows = frappe.get_attr(module)(filters)
    head = "".join(f"<th>{c['label']}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{'' if r.get(c['fieldname']) is None else r.get(c['fieldname'])}</td>" for c in cols) + "</tr>" for r in rows)
    header = "".join(f"<div>{l}</div>" for l in ph_header_lines(filters.get("company")))
    return f"<html><body style='font-family:Arial;font-size:9pt'>{header}<h3>{title}</h3><table border='1' cellspacing='0' cellpadding='2'><tr>{head}</tr>{body}</table></body></html>"


BOOK_REPORTS = [
    ("General Journal", "ph_cas.ph_cas.report.ph_general_journal.ph_general_journal.execute"),
    ("General Ledger", "ph_cas.ph_cas.report.ph_general_ledger_book.ph_general_ledger_book.execute"),
    ("Cash Receipts Book", "ph_cas.ph_cas.report.ph_cash_receipts_book.ph_cash_receipts_book.execute"),
    ("Cash Disbursements Book", "ph_cas.ph_cas.report.ph_cash_disbursements_book.ph_cash_disbursements_book.execute"),
    ("Sales Journal", "ph_cas.ph_cas.report.ph_sales_journal.ph_sales_journal.execute"),
    ("Purchase Journal", "ph_cas.ph_cas.report.ph_purchase_journal.ph_purchase_journal.execute"),
    ("Inventory Book", "ph_cas.ph_cas.report.ph_inventory_book.ph_inventory_book.execute"),
]


def build(company: str) -> dict:
    files = {}
    files["01_Annex_C1_System_Description.txt"] = annex_c1(company).encode("utf-8")
    answers, gaps = annex_b_answers(company)
    files["02_Annex_B_Answers.txt"] = answers.encode("utf-8")
    files["03_Joint_Sworn_Statement.txt"] = joint_sworn_statement(company).encode("utf-8")
    files["03a_Notice_of_Third_Party_Custody.txt"] = custody_notice(company).encode("utf-8")
    files["04_Conformance_Report.txt"] = conformance_report().encode("utf-8")
    specimens = {
        "05_Sample_Sales_Invoice.html": _render("Sales Invoice", _latest("Sales Invoice", {"company": company, "is_return": 0, "is_debit_note": 0}), "PH Sales Invoice"),
        "06_Sample_Credit_Note.html": _render("Sales Invoice", _latest("Sales Invoice", {"company": company, "is_return": 1}), "PH Sales Invoice"),
        "07_Sample_Collection_Receipt.html": _render("Payment Entry", _latest("Payment Entry", {"company": company, "payment_type": "Receive"}), "PH Collection Receipt"),
        "08_Sample_2307.pdf": _bir_2307(_latest("PH 2307 Issued", {"company": company})),
    }
    missing = [k for k, v in specimens.items() if not v]
    files.update({k: v if isinstance(v, bytes) else v.encode("utf-8") for k, v in specimens.items() if v})
    f = {"company": company, "from_date": get_first_day(nowdate()), "to_date": get_last_day(nowdate())}
    for i, (title, module) in enumerate(BOOK_REPORTS, 9):
        files[f"{i:02d}_Book_{title.replace(' ', '_')}.html"] = _report_html(title, module, f).encode("utf-8")
    files["16_Audit_Trail_30_days.html"] = _report_html("BIR Audit Trail (last 30 days)", "ph_cas.ph_cas.report.bir_audit_trail.bir_audit_trail.execute", {"company": company, "from_date": add_days(now_datetime(), -30), "to_date": now_datetime()}).encode("utf-8")
    files["17_Chain_Check.html"] = _report_html("PH Chain Check", "ph_cas.ph_cas.report.ph_chain_check.ph_chain_check.execute", {"company": company}).encode("utf-8")
    manifest = {"company": company, "generated_on": now_datetime().strftime("%Y-%m-%d %H:%M:%S"), "by": frappe.session.user, "software": f"{software_name()} {platform_version()}", "annex_b_gaps": [g["item"] for g in gaps], "specimens_missing": missing, "files": sorted(files)}
    files["00_MANIFEST.json"] = json.dumps(manifest, indent=1).encode("utf-8")
    return {"files": files, "gaps": gaps, "missing": missing, "manifest": manifest}


@frappe.whitelist()
def download_pack(company: str):
    frappe.has_permission("Company", "write", company, throw=True)
    out = build(company)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in out["files"].items():
            z.writestr(name, content)
    frappe.response["type"] = "binary"
    frappe.response["filename"] = f"registration_pack_{company}.zip".replace(" ", "_")
    frappe.response["filecontent"] = buf.getvalue()
    from ph_cas.audit.events import record

    record("export", "Company", company, 0, {"registration_pack": out["manifest"]["files"], "gaps": out["manifest"]["annex_b_gaps"]})
