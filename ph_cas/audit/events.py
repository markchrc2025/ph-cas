"""B07: the hash-chained event log.

Every row carries the SHA-256 of (previous hash, sequence, timestamp, user,
event, document type, document, docstatus, details). Rows are appended under
a row lock on the latest row, so parallel writers serialise. Nothing updates
or deletes a row (the DocType refuses, B02 refuses, and the chain check would
show it anyway).
"""

import hashlib
import json

import frappe

from ph_cas.branding import product_name
from frappe.utils import now_datetime

from ph_cas.controls.locks import POSTED_VOUCHER_TYPES

GENESIS = "0" * 64

MASTER_TYPES = frozenset({"Customer", "Supplier", "Item", "Account", "Company", "Cost Center", "Warehouse", "User", "Role"})
SETTINGS_TYPES = frozenset({"System Settings", "Accounts Settings", "Stock Settings", "Selling Settings", "Buying Settings", "PH CAS Settings", "BIR Series", "Accounting Period", "Document Naming Settings", "Print Settings"})
PERMISSION_TYPES = frozenset({"Custom DocPerm", "DocPerm", "User Permission", "Role Profile", "Has Role"})

TRACKED_FOR_CREATE = POSTED_VOUCHER_TYPES | MASTER_TYPES | SETTINGS_TYPES | PERMISSION_TYPES


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(previous_hash, seq, timestamp, user, event, ref_doctype, ref_name, docstatus_after, details) -> str:
    material = _canonical(
        {
            "previous_hash": previous_hash,
            "seq": int(seq),
            "timestamp": str(timestamp),
            "user": user or "",
            "event": event,
            "ref_doctype": ref_doctype or "",
            "ref_name": ref_name or "",
            "docstatus_after": int(docstatus_after or 0),
            "details": details or "",
        }
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def record(event: str, ref_doctype: str | None = None, ref_name: str | None = None, docstatus_after: int = 0, details: dict | None = None, user: str | None = None):
    """Append one row. Safe to call from any hook; never raises into the caller's
    transaction except on a genuine database error."""
    if frappe.flags.get("ph_event_log_disabled"):
        return None
    last = frappe.db.sql(
        "select seq, hash from `tabPH Event Log` order by seq desc limit 1 for update", as_dict=True
    )
    previous_hash = last[0].hash if last else GENESIS
    seq = (int(last[0].seq) + 1) if last else 1
    timestamp = now_datetime().strftime("%Y-%m-%d %H:%M:%S.%f")
    user = user or frappe.session.user
    details_json = _canonical(details or {})
    h = compute_hash(previous_hash, seq, timestamp, user, event, ref_doctype, ref_name, docstatus_after, details_json)
    frappe.flags.ph_event_log_writer = True
    try:
        row = frappe.get_doc(
            {
                "doctype": "PH Event Log",
                "seq": seq,
                "timestamp": timestamp,
                "user": user,
                "event": event,
                "ref_doctype": ref_doctype,
                "ref_name": ref_name,
                "docstatus_after": docstatus_after,
                "details": details_json,
                "previous_hash": previous_hash,
                "hash": h,
            }
        )
        row.flags.ignore_permissions = True
        row.insert()
    finally:
        frappe.flags.ph_event_log_writer = False
    return row


def verify_chain(start_seq: int = 1) -> dict:
    """Recompute every hash. Returns {ok, checked, first_bad_seq, reason}."""
    rows = frappe.db.sql(
        "select seq, timestamp, user, event, ref_doctype, ref_name, docstatus_after, details, previous_hash, hash from `tabPH Event Log` where seq >= %s order by seq",
        start_seq,
        as_dict=True,
    )
    previous = GENESIS
    if start_seq > 1:
        prev_row = frappe.db.get_value("PH Event Log", {"seq": start_seq - 1}, "hash")
        previous = prev_row or GENESIS
    expected_seq = start_seq
    for r in rows:
        if int(r.seq) != expected_seq:
            return {"ok": False, "checked": expected_seq - start_seq, "first_bad_seq": expected_seq, "reason": "gap in sequence"}
        if r.previous_hash != previous:
            return {"ok": False, "checked": expected_seq - start_seq, "first_bad_seq": r.seq, "reason": "previous hash does not match"}
        ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f") if hasattr(r.timestamp, "strftime") else str(r.timestamp)
        h = compute_hash(r.previous_hash, r.seq, ts, r.user, r.event, r.ref_doctype, r.ref_name, r.docstatus_after, r.details)
        if h != r.hash:
            return {"ok": False, "checked": expected_seq - start_seq, "first_bad_seq": r.seq, "reason": "row content does not match its hash"}
        previous = r.hash
        expected_seq += 1
    return {"ok": True, "checked": len(rows), "first_bad_seq": None, "reason": None}


def daily_chain_check():
    """scheduler_events.daily"""
    result = verify_chain()
    frappe.db.set_value("PH CAS Settings", None, {"last_chain_check": now_datetime(), "last_chain_check_ok": 1 if result["ok"] else 0}, update_modified=False)
    if not result["ok"]:
        recipients = [
            u["parent"]
            for u in frappe.get_all("Has Role", filters={"role": "System Manager", "parenttype": "User"}, fields=["parent"])
            if u["parent"] != "Administrator" and frappe.db.get_value("User", u["parent"], "enabled")
        ]
        if recipients:
            frappe.sendmail(
                recipients=recipients,
                subject=f"{product_name()} event log chain check FAILED",
                message=f"The event log chain is broken at sequence {result['first_bad_seq']}: {result['reason']}. Investigate before anything else.",
            )
    return result


# ---- hook writers ---------------------------------------------------------


def _diff(doc) -> dict:
    before = doc.get_doc_before_save()
    if not before:
        return {}
    changes = {}
    for df in doc.meta.fields:
        if df.fieldtype in frappe.model.table_fields or df.fieldtype in ("Section Break", "Column Break", "Tab Break", "HTML", "Button"):
            continue
        if df.fieldtype == "Password":
            continue
        a, b = before.get(df.fieldname), doc.get(df.fieldname)
        if (a or None) != (b or None) and str(a) != str(b):
            changes[df.fieldname] = [a, b]
    for tf in doc.meta.get_table_fields():
        a = [{k: v for k, v in r.as_dict().items() if k not in ("name", "idx", "creation", "modified", "modified_by", "owner", "docstatus", "parent", "parentfield", "parenttype", "doctype")} for r in before.get(tf.fieldname) or []]
        b = [{k: v for k, v in r.as_dict().items() if k not in ("name", "idx", "creation", "modified", "modified_by", "owner", "docstatus", "parent", "parentfield", "parenttype", "doctype")} for r in doc.get(tf.fieldname) or []]
        if _canonical(a) != _canonical(b):
            changes[tf.fieldname] = {"rows_before": len(a), "rows_after": len(b)}
    return changes


def on_after_insert(doc, method=None):
    if doc.doctype in POSTED_VOUCHER_TYPES or doc.doctype in MASTER_TYPES or doc.doctype in PERMISSION_TYPES:
        details = {}
        if doc.doctype in PERMISSION_TYPES:
            details = {k: doc.get(k) for k in ("role", "parent", "allow", "for_value", "user", "permlevel", "read", "write", "create", "delete", "submit", "cancel", "amend") if doc.meta.has_field(k)}
        record("create", doc.doctype, doc.name, doc.docstatus, details)


def on_update(doc, method=None):
    if doc.doctype in SETTINGS_TYPES:
        changes = _diff(doc)
        if changes or doc.is_new():
            record("settings_change", doc.doctype, doc.name, doc.docstatus, changes)
    elif doc.doctype == "User":
        changes = _diff(doc)
        if "enabled" in changes:
            record("user_deactivated" if not doc.enabled else "user_reactivated", "User", doc.name, 0, {"enabled": changes["enabled"]})
        if "roles" in changes or any(k in changes for k in ("role_profile_name", "module_profile")):
            record("role_change", "User", doc.name, 0, {"roles": sorted(r.role for r in doc.roles)})
    elif doc.doctype in MASTER_TYPES and not doc.is_new():
        changes = _diff(doc)
        if changes:
            record("master_change", doc.doctype, doc.name, doc.docstatus, changes)


def on_submit(doc, method=None):
    if doc.doctype in POSTED_VOUCHER_TYPES:
        details = {"grand_total": doc.get("grand_total"), "posting_date": doc.get("posting_date")}
        if doc.get("bir_serial"):
            details["bir_serial"] = doc.get("bir_serial")
        if doc.get("amended_from"):
            details["amended_from"] = doc.get("amended_from")
        record("amend" if doc.get("amended_from") else "submit", doc.doctype, doc.name, 1, details)


def on_cancel(doc, method=None):
    if doc.doctype in POSTED_VOUCHER_TYPES:
        record("cancel", doc.doctype, doc.name, 2, {"grand_total": doc.get("grand_total")})


def on_update_after_submit(doc, method=None):
    if doc.doctype in POSTED_VOUCHER_TYPES:
        changes = _diff(doc)
        if changes:
            record("posted_edit", doc.doctype, doc.name, doc.docstatus, changes)


def on_trash(doc, method=None):
    if doc.doctype in POSTED_VOUCHER_TYPES or doc.doctype in MASTER_TYPES or doc.doctype in PERMISSION_TYPES:
        record("delete", doc.doctype, doc.name, doc.docstatus, {})


def on_before_print(doc, method=None, *args, **kwargs):
    if doc.doctype in POSTED_VOUCHER_TYPES:
        record("print", doc.doctype, doc.name, doc.docstatus, {"bir_serial": doc.get("bir_serial")})


def on_access_log(doc, method=None):
    """Access Log after_insert: exports, downloads, PDFs."""
    kind = (doc.get("export_from") or doc.get("file_type") or doc.get("method") or "").lower()
    event = "export"
    if doc.get("method") == "Print":
        event = "print"
    elif doc.get("file_type") == "PDF":
        event = "pdf"
    record(event, doc.get("export_from") or doc.get("reference_document") or doc.get("report_name"), doc.get("reference_document"), 0, {"file_type": doc.get("file_type"), "method": doc.get("method"), "filters": doc.get("filters"), "report": doc.get("report_name")}, user=doc.get("user"))


def on_activity_log(doc, method=None):
    if doc.get("operation") != "Login":
        return
    if doc.get("status") == "Failed":
        record("signin_failed", "User", doc.get("user"), 0, {"message": doc.get("subject")}, user=doc.get("user"))


def on_login(login_manager=None):
    record("signin", "User", frappe.session.user, 0, {"ip": frappe.local.request_ip if hasattr(frappe.local, "request_ip") else None})


def on_logout(login_manager=None):
    record("signout", "User", frappe.session.user, 0, {})
