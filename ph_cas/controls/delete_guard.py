"""B83 (LDG-214, LDG-222): Frappe refuses to delete a submitted record with its own message
("Submitted Record cannot be deleted. You must Cancel it first.") before any app hook runs.
For a posted voucher or a filed return that message is wrong: cancelling is not allowed either.
These wrappers give the app's own message first, then hand over to Frappe."""

import json

import frappe
from frappe import _


def _guard(doctype: str, name: str):
    if not frappe.db.exists(doctype, name) or not frappe.has_permission(doctype, "read", name):
        return  # Frappe's own checks answer
    docstatus = frappe.db.get_value(doctype, name, "docstatus")
    if docstatus not in (1, 2):
        return
    doc = frappe.get_doc(doctype, name)
    if doctype == "PH Tax Return" and docstatus == 1:
        from ph_cas.ph_cas.doctype.ph_tax_return.ph_tax_return import SEALED

        frappe.throw(_(SEALED), frappe.ValidationError)
    from ph_cas.controls.locks import refuse_delete

    refuse_delete(doc)


@frappe.whitelist(methods=["POST", "DELETE"])
def delete(doctype: str, name: str):
    _guard(doctype, name)
    from frappe.client import delete as original

    return original(doctype, name)


@frappe.whitelist(methods=["POST", "DELETE"])
def delete_items():
    items = json.loads(frappe.form_dict.get("items") or "[]")
    doctype = frappe.form_dict.get("doctype")
    for name in items:
        _guard(doctype, name)
    from frappe.desk.reportview import delete_items as original

    return original()


@frappe.whitelist()
def get_linked_docs_to_delete(doctype: str, name: str):
    """B94 (owner's JP-003, 27 Nov 2026): the form's Delete first asks Frappe which linked
    records would go too; for a posted voucher that lookup hits the ledger rows and answered
    "no permission for GL Entry". The app's own message comes first now."""
    _guard(doctype, name)
    from frappe.desk.form.linked_with import get_linked_docs_to_delete as original

    return original(doctype=doctype, name=name)
