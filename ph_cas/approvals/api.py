"""Whitelisted calls for the form panel and the home page."""

import frappe

from ph_cas.approvals import chains, requests


@frappe.whitelist()
def status(doctype: str, name: str) -> dict:
    if not frappe.has_permission(doctype, "read", name):
        frappe.throw("Not permitted", frappe.PermissionError)
    return requests.status_for(doctype, name)


@frappe.whitelist()
def request(doctype: str, name: str, reason: str = "") -> str:
    return requests.open_request(doctype, name, reason)


@frappe.whitelist()
def decide(request: str, decision: str, comment: str = "") -> dict:
    return requests.decide(request, decision, comment)


@frappe.whitelist()
def withdraw(request: str) -> dict:
    return requests.withdraw(request)


@frappe.whitelist()
def pending() -> list[dict]:
    return requests.pending_for()


@frappe.whitelist()
def from_template(template: str, document_type: str, company: str | None = None, group: str | None = None) -> str:
    frappe.only_for(("Accounts Manager", "PH Accounting Manager", "System Manager"))
    return chains.from_template(template, document_type, company or None, group or None).name


@frappe.whitelist()
def templates() -> dict:
    return {k: v["title"] for k, v in chains.TEMPLATES.items()}
