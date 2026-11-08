"""B08: the Annex B header. Every printout and e-copy shows the taxpayer's
name, address and TIN with branch code, the software name and version, the
user who printed it and the date and time (Annex B item 4; RMO 9-2021).

`ph_header(doc)` is a Jinja global (hooks.jinja) used by the "BIR Header"
Letter Head, by ph_cas print formats and by query-report prints (Frappe v16
renders the letter head server side with the report filters as `doc`).
`ph_header_lines(company)` gives the same facts as plain lines for the first
rows of CSV and Excel exports.
"""

import html

import frappe
from frappe.utils import now_datetime

import ph_cas


def software_name() -> str:
    name = frappe.db.get_single_value("PH CAS Settings", "product_name") if frappe.db.exists("DocType", "PH CAS Settings") else None
    return (name or "PH CAS").strip()


def software_version() -> str:
    try:
        erp = frappe.get_attr("erpnext.__version__")
    except Exception:
        erp = "?"
    return f"{ph_cas.__version__} (ERPNext {erp}, Frappe {frappe.__version__})"


def _company_of(doc) -> str | None:
    if not doc:
        return frappe.defaults.get_user_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")
    if isinstance(doc, dict):
        return doc.get("company") or frappe.defaults.get_user_default("company")
    return getattr(doc, "company", None) or frappe.defaults.get_user_default("company")


def company_facts(company: str | None) -> dict:
    facts = {"name": "", "address": "", "tin": "", "branch": "00000", "vat_status": ""}
    if not company or not frappe.db.exists("Company", company):
        return facts
    c = frappe.get_cached_doc("Company", company)
    facts["name"] = (c.get("ph_registered_name") or c.company_name or "").strip()
    tin = (c.get("tax_id") or "").strip()
    facts["tin"] = tin
    facts["branch"] = (c.get("ph_branch_code") or "00000").strip() or "00000"
    facts["vat_status"] = c.get("ph_vat_status") or ""
    facts["address"] = _company_address(company)
    return facts


def _company_address(company: str) -> str:
    try:
        from frappe.contacts.doctype.address.address import get_default_address

        name = get_default_address("Company", company)
        if not name:
            return ""
        a = frappe.get_cached_doc("Address", name)
        parts = [a.address_line1, a.address_line2, a.city, a.state, a.pincode]
        return ", ".join(p.strip() for p in parts if p and p.strip())
    except Exception:
        return ""


def ph_header_lines(company: str | None = None, user: str | None = None) -> list[str]:
    f = company_facts(company)
    tin = f"{f['tin']}-{f['branch']}" if f["tin"] else f"(TIN not set)-{f['branch']}"
    status = f" {f['vat_status']}" if f["vat_status"] else ""
    return [
        f["name"] or "(registered name not set)",
        f["address"] or "(address not set)",
        f"{'VAT' if f['vat_status'] == 'VAT' else 'NON-VAT' if f['vat_status'] else ''} REG TIN {tin}".strip(),
        f"Software: {software_name()} version {software_version()}",
        f"Printed by: {user or frappe.session.user}",
        f"Printed on: {now_datetime().strftime('%Y-%m-%d %H:%M:%S')}",
    ]


def ph_header(doc=None, company: str | None = None) -> str:
    lines = ph_header_lines(company or _company_of(doc))
    rows = "".join(f"<div>{html.escape(line)}</div>" for line in lines)
    return (
        '<div class="ph-bir-header" style="font-size:9pt;line-height:1.25;border-bottom:1px solid #999;'
        'padding-bottom:4px;margin-bottom:8px;">'
        f"{rows}</div>"
    )


def setup():
    """Create the BIR Header letter head and make it the default. Idempotent."""
    name = "BIR Header"
    if not frappe.db.exists("Letter Head", name):
        frappe.get_doc(
            {
                "doctype": "Letter Head",
                "letter_head_name": name,
                "source": "HTML",
                "content": "{{ ph_header(doc) }}",
                "is_default": 1,
            }
        ).insert(ignore_permissions=True)
    elif not frappe.db.exists("Letter Head", {"is_default": 1}):
        frappe.db.set_value("Letter Head", name, "is_default", 1)
