"""The submit gate and the change watch, hooked on every doctype.

before_submit: when an enabled chain applies (module on, more than one user),
the document submits only through an approved request: the one the engine is
posting right now, or an approved and unchanged one the maker submits by hand
after a failed post. Either is consumed once. Otherwise the submit is refused
with "Request approval".

on_update: a change to a document with an open request voids the request.
"""

import frappe
from frappe import _

from ph_cas.approvals import chains, requests

SKIP = frozenset({"PH Approval Request", "PH Approval Chain", "PH Approval Group", "PH Approval Lookup", "PH Event Log", "PH Print Record", "File", "Comment", "Version", "Communication", "Error Log", "Access Log", "Activity Log", "Email Queue", "Notification Log", "ToDo", "DocType", "Custom Field", "Property Setter"})


def _skip(doc) -> bool:
    return doc.doctype in SKIP or frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch or not chains.module_on()


def before_submit(doc, method=None):
    if _skip(doc) or doc.doctype == "PH Tax Return":
        return  # a return is filed with its BIR confirmation; its chain gates changes after filing
    if frappe.flags.get("ph_approval_submit"):
        requests.consume(frappe.flags.ph_approval_submit)
        return
    chain = chains.chain_for(doc, "Submit")
    if chain is None or chains.single_user_site():
        return
    req = requests.latest(doc.doctype, doc.name, ("Approved",))
    if req is not None and req.fingerprint == requests.fingerprint(doc):
        requests.consume(req.name)
        return
    frappe.throw(_("{0} needs approval ({1}). Use Request approval; it posts when the chain approves it.").format(f"{doc.doctype} {doc.name}", chain.title), frappe.ValidationError)


def before_cancel(doc, method=None):
    """B84: a posted document a Cancel chain applies to is cancelled only through an
    approved request (the engine cancelling it now, or the maker after a failed cancel)."""
    if _skip(doc) or doc.doctype == "PH Tax Return":
        return
    if frappe.flags.get("ph_approval_cancel"):
        requests.consume(frappe.flags.ph_approval_cancel)
        return
    chain = chains.chain_for(doc, "Cancel")
    if chain is None or chains.single_user_site():
        return
    req = requests.latest(doc.doctype, doc.name, ("Approved",))
    if req is not None and req.fingerprint == requests.fingerprint(doc):
        requests.consume(req.name)
        return
    frappe.throw(_("{0} needs approval to be cancelled ({1}). Use Request cancellation; it is cancelled when the chain approves it.").format(f"{doc.doctype} {doc.name}", chain.title), frappe.ValidationError)


def on_update(doc, method=None):
    if _skip(doc) or doc.flags.get("ph_approval_skip_void"):
        return
    if frappe.flags.get("ph_approval_submit"):
        return
    requests.void_if_changed(doc)
