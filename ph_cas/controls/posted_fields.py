"""B03: nothing posted can be changed or renumbered.

Two layers. Property setters turn `allow_on_submit` off on every accounting
field of the posted voucher types, so Frappe's own update-after-submit check
refuses the change. The `before_update_after_submit` hook then diffs the
document against the database and refuses any change outside the explicit
allowlist below, which covers child tables and anything a later ERPNext
release might turn on.
"""

import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from ph_cas.controls.locks import POSTED_VOUCHER_TYPES, PHLockError, locks_active

# Presentation and reference fields that may change after submit. Nothing here
# reaches the ledger, a tax figure, a party or a number.
ALLOWED_AFTER_SUBMIT = frozenset(
    {
        "letter_head",
        "select_print_heading",
        "group_same_items",
        "print_without_amount",
        "page_break",
        "title",
        "po_no",
        "po_date",
        "pay_to_recd_from",
        "dispatch_address_name",
        "dispatch_address",
        "sales_team",
        "auto_repeat",
        "update_auto_repeat_reference",
        "from_date",
        "to_date",
        # read-only stock displays refreshed by ERPNext
        "actual_qty",
        "actual_batch_qty",
        "company_total_stock",
        # RR 3-2024 claim flags, set after submit through ph_cas.tax.ovc (B16)
        "ph_ovc_claimed",
        "ph_ovc_claim_quarter",
        "ph_supplier_claimed_ovc",
    }
)

# Fields Frappe maintains itself on every save.
_SYSTEM_FIELDS = frozenset(
    {"modified", "modified_by", "_user_tags", "_comments", "_assign", "_liked_by", "idx", "docstatus"}
)


def _child_doctypes(doctype: str) -> list[str]:
    meta = frappe.get_meta(doctype)
    return [df.options for df in meta.get_table_fields()]


def install_property_setters():
    """Called from setup_all. Idempotent: writes a setter only where one is missing."""
    for doctype in sorted(POSTED_VOUCHER_TYPES):
        if not frappe.db.exists("DocType", doctype):
            continue
        for dt in [doctype, *_child_doctypes(doctype)]:
            meta = frappe.get_meta(dt)
            for df in meta.fields:
                if not df.allow_on_submit or df.fieldname in ALLOWED_AFTER_SUBMIT:
                    continue
                if frappe.db.exists(
                    "Property Setter",
                    {"doc_type": dt, "field_name": df.fieldname, "property": "allow_on_submit"},
                ):
                    continue
                make_property_setter(dt, df.fieldname, "allow_on_submit", 0, "Check", validate_fields_for_doctype=False)
    frappe.clear_cache()


def refuse_posted_field_changes(doc, method=None):
    """doc_events['*'].before_update_after_submit"""
    if not locks_active() or doc.doctype not in POSTED_VOUCHER_TYPES:
        return
    db_doc = frappe.get_doc(doc.doctype, doc.name)
    changed = _changed_fields(doc, db_doc)
    refused = [c for c in changed if c[1] not in ALLOWED_AFTER_SUBMIT]
    if refused:
        where, field = refused[0][0], refused[0][1]
        if doc.doctype == "Sales Invoice" and doc.get("bir_serial"):
            # an issued invoice is never cancelled (controls/cancel): corrections are notes
            remedy = _("issue a credit note for the full amount or the difference, or a debit note for an increase")
        else:
            remedy = _("cancel and reissue, or post an adjusting entry")
        frappe.throw(
            _("{0} {1} has been posted. {2} cannot be changed; {3}.").format(doc.doctype, doc.name, f"{where}.{field}", remedy),
            PHLockError,
        )


def _changed_fields(doc, db_doc):
    changed = []
    for df in doc.meta.fields:
        if df.fieldtype in frappe.model.table_fields or df.is_virtual:
            continue
        if _differs(doc.get(df.fieldname), db_doc.get(df.fieldname)):
            changed.append((doc.doctype, df.fieldname))
    for tf in doc.meta.get_table_fields():
        db_rows = {row.name: row for row in db_doc.get(tf.fieldname) or []}
        rows = doc.get(tf.fieldname) or []
        if len(rows) != len(db_rows):
            changed.append((doc.doctype, tf.fieldname))
            continue
        for row in rows:
            db_row = db_rows.get(row.name)
            if db_row is None:
                changed.append((doc.doctype, tf.fieldname))
                continue
            for cdf in row.meta.fields:
                if cdf.is_virtual or cdf.fieldname in _SYSTEM_FIELDS:
                    continue
                if _differs(row.get(cdf.fieldname), db_row.get(cdf.fieldname)):
                    changed.append((tf.options, cdf.fieldname))
    return changed


def _differs(a, b) -> bool:
    if (a in (None, "", 0, 0.0)) and (b in (None, "", 0, 0.0)):
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) > 1e-9
    return str(a) != str(b)
