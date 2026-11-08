"""BIR Audit Trail: one time-ordered list of everything the system recorded,
merged from the hash-chained PH Event Log and Frappe's own Version, Deleted
Document, Access Log and Activity Log."""

import json

import frappe
from frappe import _
from frappe.utils import get_datetime

SOURCES = ("Event Log", "Version", "Deleted Document", "Access Log", "Activity Log")


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = [
        {"fieldname": "timestamp", "label": _("Date and time"), "fieldtype": "Datetime", "width": 165},
        {"fieldname": "user", "label": _("User"), "fieldtype": "Data", "width": 160},
        {"fieldname": "source", "label": _("Source"), "fieldtype": "Data", "width": 110},
        {"fieldname": "event", "label": _("Event"), "fieldtype": "Data", "width": 110},
        {"fieldname": "ref_doctype", "label": _("Document type"), "fieldtype": "Data", "width": 140},
        {"fieldname": "ref_name", "label": _("Document"), "fieldtype": "Dynamic Link", "options": "ref_doctype", "width": 170},
        {"fieldname": "details", "label": _("Details"), "fieldtype": "Small Text", "width": 420},
        {"fieldname": "hash", "label": _("Hash"), "fieldtype": "Data", "width": 120},
    ]
    sources = _sources(filters)
    rows = []
    if "Event Log" in sources:
        rows += _event_log(filters)
    if "Version" in sources:
        rows += _versions(filters)
    if "Deleted Document" in sources:
        rows += _deleted(filters)
    if "Access Log" in sources:
        rows += _access(filters)
    if "Activity Log" in sources:
        rows += _activity(filters)
    rows.sort(key=lambda r: (get_datetime(r["timestamp"]), r.get("seq") or 0))
    return columns, rows


def _sources(filters):
    raw = filters.get("sources")
    if not raw:
        return set(SOURCES)
    if isinstance(raw, str):
        return {s.strip() for s in raw.split(",") if s.strip()}
    return set(raw)


def _common(filters, table, ts_field, user_field=None, dt_field=None, dn_field=None):
    conds = [f"`{ts_field}` between %(from_date)s and %(to_date)s"]
    if filters.get("user") and user_field:
        conds.append(f"`{user_field}` = %(user)s")
    if filters.get("ref_doctype") and dt_field:
        conds.append(f"`{dt_field}` = %(ref_doctype)s")
    if filters.get("ref_name") and dn_field:
        conds.append(f"`{dn_field}` = %(ref_name)s")
    return " and ".join(conds)


def _event_log(filters):
    where = _common(filters, "PH Event Log", "timestamp", "user", "ref_doctype", "ref_name")
    out = []
    for r in frappe.db.sql(f"select seq, timestamp, user, event, ref_doctype, ref_name, details, hash from `tabPH Event Log` where {where} order by seq", filters, as_dict=True):
        out.append({"timestamp": r.timestamp, "user": r.user, "source": "Event Log", "event": r.event, "ref_doctype": r.ref_doctype, "ref_name": r.ref_name, "details": _short(r.details), "hash": (r.hash or "")[:16], "seq": r.seq})
    return out


def _versions(filters):
    where = _common(filters, "Version", "creation", "owner", "ref_doctype", "docname")
    out = []
    for r in frappe.db.sql(f"select creation, owner, ref_doctype, docname, data from `tabVersion` where {where}", filters, as_dict=True):
        out.append({"timestamp": r.creation, "user": r.owner, "source": "Version", "event": "field change", "ref_doctype": r.ref_doctype, "ref_name": r.docname, "details": _version_summary(r.data), "hash": ""})
    return out


def _deleted(filters):
    where = _common(filters, "Deleted Document", "creation", "owner", "deleted_doctype", "deleted_name")
    out = []
    for r in frappe.db.sql(f"select creation, owner, deleted_doctype, deleted_name from `tabDeleted Document` where {where}", filters, as_dict=True):
        out.append({"timestamp": r.creation, "user": r.owner, "source": "Deleted Document", "event": "delete", "ref_doctype": r.deleted_doctype, "ref_name": r.deleted_name, "details": "", "hash": ""})
    return out


def _access(filters):
    where = _common(filters, "Access Log", "creation", "user", "export_from", "reference_document")
    out = []
    for r in frappe.db.sql(f"select creation, user, export_from, reference_document, method, file_type, report_name, page from `tabAccess Log` where {where}", filters, as_dict=True):
        out.append({"timestamp": r.creation, "user": r.user, "source": "Access Log", "event": (r.method or "access").lower(), "ref_doctype": r.export_from or r.report_name, "ref_name": r.reference_document, "details": f"{r.file_type or ''} {r.report_name or ''} {r.page or ''}".strip(), "hash": ""})
    return out


def _activity(filters):
    where = _common(filters, "Activity Log", "creation", "user")
    out = []
    for r in frappe.db.sql(f"select creation, user, operation, status, subject, ip_address from `tabActivity Log` where {where} and operation in ('Login','Logout')", filters, as_dict=True):
        out.append({"timestamp": r.creation, "user": r.user, "source": "Activity Log", "event": f"{(r.operation or '').lower()} {(r.status or '').lower()}".strip(), "ref_doctype": "User", "ref_name": r.user, "details": f"{r.subject or ''} {r.ip_address or ''}".strip(), "hash": ""})
    return out


def _short(details):
    if not details:
        return ""
    try:
        d = json.loads(details)
    except Exception:
        return str(details)[:300]
    if not d:
        return ""
    return "; ".join(f"{k}: {v}" for k, v in d.items())[:300]


def _version_summary(data):
    try:
        d = json.loads(data or "{}")
    except Exception:
        return ""
    parts = []
    for field, old, new in d.get("changed", [])[:8]:
        parts.append(f"{field}: {old} -> {new}")
    for row in d.get("row_changed", [])[:4]:
        parts.append(f"row {row[0]}#{row[1]} changed")
    if d.get("added"):
        parts.append(f"{len(d['added'])} row(s) added")
    if d.get("removed"):
        parts.append(f"{len(d['removed'])} row(s) removed")
    return "; ".join(parts)[:300]
