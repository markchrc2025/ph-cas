"""B02: nothing posted can be deleted or reposted.

Every refusal here applies to every user, Administrator included. The only
escape is `ph_cas_unlocked: 1` in site_config.json on a site that is not
marked `ph_cas_production: 1`; test code uses it to build fixtures the locks
would otherwise refuse. A production site ignores the escape.
"""

import frappe
from frappe import _


class PHLockError(frappe.ValidationError):
    pass


# Voucher types that write GL Entry, Stock Ledger Entry or Payment Ledger Entry
# rows on submit. Deletion of these is refused once docstatus is 1 or 2, even
# when no ledger row exists for them (a zero-amount voucher is still a voucher).
POSTED_VOUCHER_TYPES = frozenset(
    {
        "Sales Invoice",
        "Purchase Invoice",
        "POS Invoice",
        "Payment Entry",
        "Journal Entry",
        "Period Closing Voucher",
        "Stock Entry",
        "Delivery Note",
        "Purchase Receipt",
        "Stock Reconciliation",
        "Landed Cost Voucher",
        "Subcontracting Receipt",
        "Asset",
        "Asset Capitalization",
        "Asset Repair",
        "Asset Value Adjustment",
        "Invoice Discounting",
        "Dunning",
        "Process Deferred Accounting",
        "Payment Request",
        "Loan",
        "Expense Claim",
    }
)

LEDGER_ENTRY_TYPES = frozenset({"GL Entry", "Stock Ledger Entry", "Payment Ledger Entry"})

# DocTypes that must never come into existence on a locked site.
REFUSED_DOCTYPES = frozenset(
    {"Transaction Deletion Record", "Repost Accounting Ledger", "Repost Item Valuation"}
)


def is_production_site() -> bool:
    return bool(frappe.conf.get("ph_cas_production"))


def locks_active() -> bool:
    if is_production_site():
        return True
    return not bool(frappe.conf.get("ph_cas_unlocked"))


def has_ledger_rows(doctype: str, name: str) -> bool:
    for ledger in LEDGER_ENTRY_TYPES:
        if frappe.db.exists(ledger, {"voucher_type": doctype, "voucher_no": name}):
            return True
    return False


def refuse_delete(doc, method=None):
    """doc_events['*'].on_trash"""
    if not locks_active():
        return
    if doc.doctype in LEDGER_ENTRY_TYPES:
        frappe.throw(
            _("{0} rows are permanent. The ledger is never deleted in this system.").format(doc.doctype),
            PHLockError,
        )
    from ph_cas.controls.serial import SERIAL_FIELD

    if doc.doctype in POSTED_VOUCHER_TYPES and doc.docstatus in (1, 2) and doc.get(SERIAL_FIELD):
        # B83 (LDG-222): an issued BIR document is never cancelled either, so the message
        # points to the correction that is allowed
        frappe.throw(
            _("{0} {1} (BIR serial {2}) has been issued and cannot be deleted. Correct it with a credit note or a debit note.").format(
                doc.doctype, doc.name, doc.get(SERIAL_FIELD)
            ),
            PHLockError,
        )
    if doc.doctype in POSTED_VOUCHER_TYPES and doc.docstatus in (1, 2):
        frappe.throw(
            _("{0} {1} has been posted and cannot be deleted. Cancel it, or correct it with a new document.").format(
                doc.doctype, doc.name
            ),
            PHLockError,
        )
    if doc.docstatus in (1, 2) and has_ledger_rows(doc.doctype, doc.name):
        frappe.throw(
            _("{0} {1} has ledger entries and cannot be deleted.").format(doc.doctype, doc.name),
            PHLockError,
        )


def refuse_insert(doc, method=None):
    """doc_events[...].before_insert for REFUSED_DOCTYPES"""
    if not locks_active():
        return
    frappe.throw(
        _("{0} is disabled in this system. Posted records are never deleted or reposted.").format(doc.doctype),
        PHLockError,
    )


# Accounts Settings values the sworn statement depends on. add_taxes_from_item_tax_template is off
# because the tax engine books every VAT row itself; on, ERPNext added a zero row for each account
# of the line-scope templates (Output VAT and four Input VAT rows on a non-VAT seller's invoice; QA pass 4).
FORCED_ACCOUNTS_SETTINGS = {"enable_immutable_ledger": 1, "delete_linked_ledger_entries": 0, "add_taxes_from_item_tax_template": 0}


def validate_accounts_settings(doc, method=None):
    """doc_events['Accounts Settings'].validate"""
    if not locks_active():
        return
    for field, value in FORCED_ACCOUNTS_SETTINGS.items():
        if int(doc.get(field) or 0) != value:
            frappe.throw(
                _("Accounts Settings: {0} must stay {1} in this system.").format(
                    doc.meta.get_label(field), _("on") if value else _("off")
                ),
                PHLockError,
            )


def force_accounts_settings():
    """Called from setup_all (install and migrate). Idempotent."""
    settings = frappe.get_doc("Accounts Settings")
    changed = False
    for field, value in FORCED_ACCOUNTS_SETTINGS.items():
        if int(settings.get(field) or 0) != value:
            settings.set(field, value)
            changed = True
    if changed:
        settings.flags.ignore_permissions = True
        settings.save()
