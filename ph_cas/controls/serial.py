"""B06: the BIR serial number.

One counter per company, branch and document type (decision D4: 8 digits,
continuous, no yearly reset). The number is taken inside the submit
transaction under a row lock, so it commits or rolls back with the document.
Cancellation keeps the number. A unique index refuses duplicates.
"""

import frappe
from frappe import _

from ph_cas.controls.locks import PHLockError

SERIAL_FIELD = "bir_serial"
SERIAL_KEY_FIELD = "bir_serial_key"  # unique per company, branch and document type
BRANCH_FIELD = "ph_branch_code"

# Document types that carry a serial, and how a Sales Invoice resolves to one.
SERIAL_DOCTYPES = ("Sales Invoice", "Payment Entry")


def document_type_of(doc) -> str | None:
    if doc.doctype == "Sales Invoice":
        if doc.get("is_return"):
            return "Credit Note"
        if doc.get("is_debit_note"):
            return "Debit Note"
        return "Sales Invoice"
    if doc.doctype == "Payment Entry":
        return "Collection Receipt" if doc.get("payment_type") == "Receive" else None
    return None


def series_name(company: str, branch_code: str, document_type: str) -> str:
    return f"{document_type}-{branch_code}-{company}"


def allocate(series: str) -> tuple[str, int]:
    """Take the next number of `series` under a row lock. Returns (serial, remaining)."""
    row = frappe.db.sql(
        "select prefix, digits, next_number, range_end, disabled from `tabBIR Series` where name = %s for update",
        series,
        as_dict=True,
    )
    if not row:
        frappe.throw(_("No BIR Series exists for {0}. Create it from the Acknowledgment Certificate.").format(series), PHLockError)
    row = row[0]
    if row.disabled:
        frappe.throw(_("BIR Series {0} is disabled.").format(series), PHLockError)
    number = int(row.next_number)
    if number > int(row.range_end):
        frappe.throw(
            _("BIR Series {0} has used its registered range (last number {1}). Register a new range before issuing more documents.").format(
                series, row.range_end
            ),
            PHLockError,
        )
    frappe.db.sql("update `tabBIR Series` set next_number = %s where name = %s", (number + 1, series))
    serial = f"{row.prefix or ''}{number:0{int(row.digits or 8)}d}"
    return serial, int(row.range_end) - number


def assign_serial(doc, method=None):
    """doc_events[...].before_submit"""
    document_type = document_type_of(doc)
    if not document_type:
        return
    if doc.get(SERIAL_FIELD):
        return  # amended from a cancelled document? no: an amendment is new and gets a new number
    branch = (doc.get(BRANCH_FIELD) or "").strip()
    if not branch:
        branch = (frappe.db.get_value("Company", doc.company, "ph_branch_code") or "00000").strip() or "00000"
        doc.set(BRANCH_FIELD, branch)
    series = series_name(doc.company, branch, document_type)
    serial, remaining = allocate(series)
    doc.set(SERIAL_FIELD, serial)
    doc.set(SERIAL_KEY_FIELD, f"{series}:{serial}")
    warn_below = frappe.db.get_value("BIR Series", series, "warn_below") or 0
    if remaining < int(warn_below):
        frappe.msgprint(
            _("Only {0} numbers remain in BIR Series {1}. Register a new range soon.").format(remaining, series),
            indicator="orange",
            alert=True,
        )
        if remaining in (int(warn_below) - 1, 100, 10, 0):
            _notify(series, remaining)


def _notify(series, remaining):
    recipients = [
        u["parent"]
        for u in frappe.get_all("Has Role", filters={"role": "PH Accounting Manager", "parenttype": "User"}, fields=["parent"])
        if frappe.db.get_value("User", u["parent"], "enabled")
    ]
    if recipients:
        try:
            frappe.sendmail(
                recipients=recipients,
                subject=_("BIR Series {0}: {1} numbers left").format(series, remaining),
                message=_("Register a new range with the RDO before the series runs out."),
                delayed=True,
            )
        except Exception:
            frappe.log_error("ph_cas: series warning email failed")


def clear_serial_on_copy(doc, method=None):
    """doc_events[...].before_insert: a copy or amendment never inherits a serial."""
    if doc.meta.has_field(SERIAL_FIELD):
        doc.set(SERIAL_FIELD, None)
        doc.set(SERIAL_KEY_FIELD, None)


def setup():
    """Called from setup_all. Idempotent."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    fields = {}
    for dt in SERIAL_DOCTYPES:
        fields[dt] = [
            {
                "fieldname": BRANCH_FIELD,
                "label": "Branch code",
                "fieldtype": "Data",
                "insert_after": "company",
                "fetch_from": "company.ph_branch_code",
                "fetch_if_empty": 1,
                "default": "",
                "length": 5,
                "read_only_depends_on": "eval:doc.docstatus != 0",
                "description": "5-digit BIR branch code of the issuing branch.",
            },
            {
                "fieldname": SERIAL_FIELD,
                "label": "BIR serial no.",
                "fieldtype": "Data",
                "insert_after": BRANCH_FIELD,
                "read_only": 1,
                "unique": 0,
                "no_copy": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "bold": 1,
                "allow_on_submit": 0,
                "search_index": 1,
                "description": "Taken at submit from the BIR Series of the company, branch and document type.",
            },
            {
                "fieldname": SERIAL_KEY_FIELD,
                "label": "BIR serial key",
                "fieldtype": "Data",
                "insert_after": SERIAL_FIELD,
                "read_only": 1,
                "hidden": 1,
                "unique": 1,
                "no_copy": 1,
                "allow_on_submit": 0,
                "length": 180,
            },
        ]
    create_custom_fields(fields, ignore_validate=True, update=True)
    # An early build had a unique index on bir_serial itself; the serial is
    # unique per series, not per table, so drop that index where it exists.
    for dt in SERIAL_DOCTYPES:
        table = f"tab{dt}"
        idx = frappe.db.sql(
            "select index_name from information_schema.statistics where table_schema = database() and table_name = %s and column_name = %s and non_unique = 0",
            (table, SERIAL_FIELD),
        )
        for (index_name,) in idx:
            frappe.db.sql_ddl(f"alter table `{table}` drop index `{index_name}`")


def ensure_series(company: str, branch_code: str = "00000", **values):
    """Create the four series of a branch if missing. Used by setup actions and tests."""
    created = []
    for document_type in ("Sales Invoice", "Credit Note", "Debit Note", "Collection Receipt"):
        name = series_name(company, branch_code, document_type)
        if not frappe.db.exists("BIR Series", name):
            doc = frappe.get_doc(
                {"doctype": "BIR Series", "company": company, "branch_code": branch_code, "document_type": document_type, **values}
            )
            doc.insert(ignore_permissions=True)
            created.append(name)
    return created
