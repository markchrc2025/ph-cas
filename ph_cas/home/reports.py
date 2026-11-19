"""B79: the Reports page (/app/ph-reports), one place for every report.

Before this, the home page's Reports tile opened the BIR Audit Trail and the other reports sat in
ERPNext's module workspaces. Here they are grouped the way an accountant looks for them: books of
accounts, financial statements, receivables and payables, cash and bank, BIR, sales and purchases,
stock, projects, assets, manufacturing, and audit.

What a user sees is what they may open: a report shows only when it exists on the site, its
module is switched on (Settings > Modules) and the user's roles allow it. A group left empty is
dropped. The list itself is data (GROUPS); a new report is a new row.
"""

from __future__ import annotations

import frappe
from frappe import _

# (report or doctype, label, one-line description); kind "report" unless "doctype"
GROUPS = [
    {"key": "books", "label": "Books of accounts", "module": None, "items": [
        ("PH General Ledger Book", "General Ledger book", "Every posting by account, in the BIR book layout"),
        ("PH General Journal", "General Journal", "Journal entries and adjustments, in date order"),
        ("PH Sales Journal", "Sales Journal", "Sales invoices with VAT and withholding, per BIR"),
        ("PH Purchase Journal", "Purchase Journal", "Bills with input VAT and withholding, per BIR"),
        ("PH Cash Receipts Book", "Cash Receipts book", "Money in, by cash and bank account"),
        ("PH Cash Disbursements Book", "Cash Disbursements book", "Money out, by cash and bank account"),
        ("PH Inventory Book", "Inventory book", "Stock in and out, for the inventory list"),
    ]},
    {"key": "statements", "label": "Financial statements", "module": None, "items": [
        ("Trial Balance", "Trial Balance", "Every account's balance for a period"),
        ("Balance Sheet", "Balance Sheet", "Assets, liabilities and equity at a date"),
        ("Profit and Loss Statement", "Income Statement", "Income and expenses for a period"),
        ("Cash Flow", "Cash Flow", "Cash from operations, investing and financing"),
        ("General Ledger", "General Ledger (detail)", "Postings with filters by account, party or voucher"),
    ]},
    {"key": "ar_ap", "label": "Receivables and payables", "module": None, "items": [
        ("Accounts Receivable", "Accounts Receivable", "Open customer invoices, with ageing"),
        ("Accounts Receivable Summary", "Receivable summary", "One line per customer"),
        ("Accounts Payable", "Accounts Payable", "Open bills, with ageing"),
        ("Accounts Payable Summary", "Payable summary", "One line per supplier"),
        ("Customer Ledger Summary", "Customer ledger", "Opening, invoiced, paid and closing per customer"),
        ("Supplier Ledger Summary", "Supplier ledger", "Opening, billed, paid and closing per supplier"),
    ]},
    {"key": "cash", "label": "Cash and bank", "module": None, "items": [
        ("PH Cash Position", "Cash position", "Opening, in, out and ending per cash and bank account for a day"),
        ("Bank Reconciliation Statement", "Bank reconciliation", "Book balance against the bank statement"),
    ]},
    {"key": "bir", "label": "BIR and tax", "module": None, "items": [
        ("PH Tax Return", "Tax returns", "2550Q, 1601-EQ, 1702Q and the other returns, computed from the books", "doctype"),
        ("PH Compliance Calendar", "Compliance calendar", "What is due, and when"),
        ("PH Book to Tax Reconciliation", "Book to tax reconciliation", "The books against each return's figures"),
        ("PH 2307 Issued", "2307 issued", "Certificates given to suppliers", "doctype"),
        ("PH 2307 Received Reconciliation", "2307 received reconciliation", "Certificates from customers against what they withheld"),
        ("PH Alphalist File", "Alphalist files", "The .dat files for the BIR", "doctype"),
        ("PH VAT Threshold Watch", "VAT threshold watch", "Sales against the 3,000,000 VAT threshold"),
        ("PH SC PWD Sales", "Senior citizen and PWD sales", "Discounted sales for the SC and PWD report"),
        ("PH Draft Tax Rules", "Draft tax rules", "Tax rules waiting for review"),
    ]},
    {"key": "selling", "label": "Sales", "module": "selling", "items": [
        ("Sales Register", "Sales register", "Every sales invoice with its taxes"),
        ("Item-wise Sales Register", "Sales by item", "Sales invoice lines by item"),
        ("Gross Profit", "Gross profit", "Sales less the cost of what was sold"),
        ("Sales Analytics", "Sales analytics", "Sales by customer, item or territory over time"),
    ]},
    {"key": "buying", "label": "Purchases", "module": "buying", "items": [
        ("Purchase Register", "Purchase register", "Every bill with its taxes"),
        ("Item-wise Purchase Register", "Purchases by item", "Bill lines by item"),
        ("Purchase Analytics", "Purchase analytics", "Purchases by supplier or item over time"),
    ]},
    {"key": "stock", "label": "Stock", "module": "stock", "items": [
        ("Stock Balance", "Stock balance", "Quantity and value per item and warehouse"),
        ("Stock Ledger", "Stock ledger", "Every stock movement"),
        ("Stock Projected Qty", "Projected quantity", "On hand, ordered and reserved per item"),
    ]},
    {"key": "projects", "label": "Projects", "module": "projects", "items": [
        ("Project Summary", "Project summary", "Cost and billing per project"),
    ]},
    {"key": "assets", "label": "Fixed assets", "module": "assets", "items": [
        ("Fixed Asset Register", "Fixed asset register", "Assets, cost and book value"),
        ("Asset Depreciations and Balances", "Depreciation and balances", "Depreciation per asset category"),
    ]},
    {"key": "manufacturing", "label": "Manufacturing", "module": "manufacturing", "items": [
        ("Work Order Summary", "Work order summary", "Work orders and their status"),
        ("BOM Stock Report", "BOM stock", "Whether stock covers a bill of materials"),
    ]},
    {"key": "audit", "label": "Audit", "module": None, "items": [
        ("BIR Audit Trail", "Audit trail", "Who did what, and when"),
        ("PH Chain Check", "Chain check", "Whether the audit log is unbroken"),
        ("PH Print Record", "Print records", "Every printed invoice and receipt", "doctype"),
    ]},
]


def _report_ok(name: str, hidden_reports: set, counter: bool = False) -> bool:
    from ph_cas.setup.roles import STAFF_REPORTS

    if counter and name not in STAFF_REPORTS:
        return False
    if name in hidden_reports or not frappe.db.exists("Report", name):
        return False
    if frappe.db.get_value("Report", name, "disabled"):
        return False
    try:
        return bool(frappe.get_cached_doc("Report", name).is_permitted())
    except Exception:
        return False


def _doctype_ok(name: str, hidden_doctypes: set, counter: bool = False) -> bool:
    return not counter and name not in hidden_doctypes and frappe.db.exists("DocType", name) and frappe.has_permission(name, "read")


@frappe.whitelist()
def catalogue() -> dict:
    """The groups and reports this user may open, with routes."""
    from ph_cas.modules.api import catalogue as modules, hidden, state

    st = state()
    try:
        h = hidden()
    except Exception:
        h = {"reports": set(), "doctypes": set()}
    from ph_cas.setup.roles import counter_limited

    counter = counter_limited()
    out = []
    for g in GROUPS:
        if g["module"] and not st.get(g["module"], True):
            continue
        items = []
        for row in g["items"]:
            name, label, desc = row[:3]
            kind = row[3] if len(row) > 3 else "report"
            if kind == "doctype":
                if not _doctype_ok(name, h["doctypes"], counter):
                    continue
                route = "/app/" + frappe.scrub(name).replace("_", "-")
            else:
                if not _report_ok(name, h["reports"], counter):
                    continue
                rtype = frappe.db.get_value("Report", name, "report_type")
                route = ("/app/query-report/" if rtype in ("Script Report", "Query Report") else "/app/report/") + name
            items.append({"name": name, "label": _(label), "description": _(desc), "route": route, "kind": kind})
        if items:
            out.append({"key": g["key"], "label": _(g["label"]), "items": items})
    off = [m.get("label") or m["key"].title() for m in modules() if not st.get(m["key"], True)]
    return {"groups": out, "modules_off": off, "can_switch_modules": "System Manager" in frappe.get_roles()}
