"""B04: dates, drafts, periods, inventory (D5, D7).

- Sales documents and receipts carry the day they are posted (D5). Journal
  Entries and Purchase Invoices may be back-dated into an open period only by
  a Accounting Manager who gives a reason. Nothing is future-dated.
- Drafts of posted voucher types cannot be printed or turned into PDFs.
- Accounting Periods are created and closed by Accounting Manager only, and
  a closed period closes every posted voucher type with no exempted role.
- Perpetual inventory stays off (D7); stock documents cannot be back-dated and
  Stock Reconciliation is limited to Accounting Manager.
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from ph_cas.controls.locks import POSTED_VOUCHER_TYPES, PHLockError, locks_active

MANAGER_ROLE = "Accounting Manager"

# Posted on the day, no exceptions (D5).
SAME_DAY_DOCTYPES = frozenset(
    {
        "Sales Invoice",
        "POS Invoice",
        "Payment Entry",
        "Stock Entry",
        "Delivery Note",
        "Purchase Receipt",
        "Stock Reconciliation",
        "Subcontracting Receipt",
    }
)

# Back-dating allowed for the manager role with a written reason.
BACKDATE_WITH_REASON_DOCTYPES = frozenset({"Journal Entry", "Purchase Invoice"})

REASON_FIELD = "ph_backdate_reason"

MANAGER_ONLY_DOCTYPES = frozenset({"Accounting Period", "Stock Reconciliation"})


def today() -> str:
    return nowdate()


def validate_posting_date(doc, method=None):
    """doc_events['*'].validate"""
    if not locks_active() or doc.doctype not in POSTED_VOUCHER_TYPES:
        return
    if not doc.meta.has_field("posting_date") or not doc.get("posting_date"):
        return
    posting = getdate(doc.posting_date)
    now = getdate(today())

    if posting > now:
        frappe.throw(
            _("{0}: the posting date {1} is in the future. Documents carry the day they are posted.").format(
                doc.doctype, frappe.format(doc.posting_date, "Date")
            ),
            PHLockError,
        )

    if doc.doctype in SAME_DAY_DOCTYPES:
        if doc.get("amended_from") and doc.is_new():
            # An amendment is a new document: ERPNext copies the original's
            # date and ticks Edit Posting Date; D5 says it carries today.
            doc.set_posting_time = 0
            doc.posting_date = today()
            if doc.meta.has_field("posting_time"):
                doc.posting_time = frappe.utils.nowtime()
            posting = getdate(doc.posting_date)
        if doc.get("set_posting_time"):
            frappe.throw(
                _("{0}: Edit Posting Date and Time is not available. Documents carry the day they are posted.").format(
                    doc.doctype
                ),
                PHLockError,
            )
        if posting != now:
            frappe.throw(
                _("{0}: the posting date must be today ({1}).").format(doc.doctype, frappe.format(today(), "Date")),
                PHLockError,
            )
        return

    if doc.doctype in BACKDATE_WITH_REASON_DOCTYPES and posting != now:
        if MANAGER_ROLE not in frappe.get_roles():
            frappe.throw(
                _("{0}: only a {1} may post with an earlier date.").format(doc.doctype, MANAGER_ROLE),
                PHLockError,
            )
        if not (doc.get(REASON_FIELD) or "").strip():
            frappe.throw(
                _("{0}: give the reason for the earlier posting date in '{1}'.").format(
                    doc.doctype, _("Reason for earlier posting date")
                ),
                PHLockError,
            )


def refuse_draft_print(doc, method=None, *args, **kwargs):
    """doc_events['*'].before_print. A draft of a posted voucher type never
    leaves the system as paper or PDF."""
    if not locks_active():
        return
    if doc.doctype in POSTED_VOUCHER_TYPES and doc.docstatus == 0:
        frappe.throw(
            _("{0} {1} is a draft. Drafts cannot be printed; submit the document first.").format(
                doc.doctype, doc.name
            ),
            PHLockError,
        )


def validate_accounting_period(doc, method=None):
    """doc_events['Accounting Period'].validate: every posted voucher type is
    closed, and no role is exempted."""
    if not locks_active():
        return
    require_manager(doc)
    rows = doc.get("closed_documents") or []
    present = {_get(row, "document_type") for row in rows}
    for doctype in sorted(POSTED_VOUCHER_TYPES):
        if not frappe.db.exists("DocType", doctype):
            continue
        if doctype not in present:
            doc.append("closed_documents", {"document_type": doctype, "closed": 1})
    for row in doc.get("closed_documents") or []:
        if _get(row, "document_type") in POSTED_VOUCHER_TYPES:
            _set(row, "closed", 1)
    if doc.get("exempted_role"):
        frappe.throw(_("Accounting Period: no role may be exempted from a closed period."), PHLockError)


def _get(row, key):
    return row.get(key) if isinstance(row, dict) else getattr(row, key, None)


def _set(row, key, value):
    if isinstance(row, dict):
        row[key] = value
    else:
        setattr(row, key, value)


def require_manager(doc, method=None):
    """validate hook for MANAGER_ONLY_DOCTYPES: creating or changing one needs
    the manager role. Frappe's has_permission hooks run only with a document
    in hand, so this covers the doctype-level create check too."""
    if not locks_active():
        return
    if frappe.session.user == "Administrator":
        return
    if MANAGER_ROLE not in frappe.get_roles():
        frappe.throw(_("Only a {0} may create or change {1}.").format(MANAGER_ROLE, doc.doctype), PHLockError)


def manager_only_permission(doc, ptype=None, user=None):
    """hooks.has_permission for MANAGER_ONLY_DOCTYPES. Administrator passes
    before this is reached (Frappe behaviour)."""
    if not locks_active():
        return True
    if ptype in ("read", "report", "export", "print", "email", "select"):
        return True
    return MANAGER_ROLE in frappe.get_roles(user)


def validate_company_inventory(doc, method=None):
    """doc_events['Company'].validate (D7)."""
    if not locks_active():
        return
    if doc.is_new():
        doc.enable_perpetual_inventory = 0  # ERPNext's default is on; D7 says off
        return
    if doc.get("enable_perpetual_inventory"):
        frappe.throw(
            _("Perpetual inventory stays off in this system (decision D7). Stock is valued periodically."),
            PHLockError,
        )


def setup():
    """Called from setup_all. Idempotent."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    if frappe.db.exists("Role", "PH Accounting Manager"):  # the role's earlier name (patch v0)
        from ph_cas.patches.v0.rename_accounting_manager_role import execute

        execute()
    if not frappe.db.exists("Role", MANAGER_ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": MANAGER_ROLE, "desk_access": 1}).insert(
            ignore_permissions=True
        )
    fields = {}
    for doctype in sorted(BACKDATE_WITH_REASON_DOCTYPES):
        if frappe.db.exists("DocType", doctype):
            fields[doctype] = [
                {
                    "fieldname": REASON_FIELD,
                    "label": "Reason for earlier posting date",
                    "fieldtype": "Small Text",
                    "insert_after": "posting_date",
                    "depends_on": "eval:doc.posting_date && doc.posting_date != frappe.datetime.get_today()",
                    "allow_on_submit": 0,
                    "no_copy": 1,
                    "description": "Required when the posting date is earlier than today. Only a Accounting Manager may do this.",
                }
            ]
    if fields:
        create_custom_fields(fields, ignore_validate=True, update=True)

    if frappe.db.get_single_value("System Settings", "time_zone") != "Asia/Manila":
        frappe.db.set_single_value("System Settings", "time_zone", "Asia/Manila")

    # Perpetual inventory off where no stock ledger exists yet (D7)
    for company in frappe.get_all("Company", filters={"enable_perpetual_inventory": 1}, pluck="name"):
        if not frappe.db.exists("Stock Ledger Entry", {"company": company, "is_cancelled": 0}):
            frappe.db.set_value("Company", company, "enable_perpetual_inventory", 0, update_modified=False)
    frappe.clear_cache()
