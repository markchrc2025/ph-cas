"""Small fixtures for tests. Everything is created once and reused."""

import frappe
from frappe.utils import today

from ph_cas.tests.setup import TEST_ABBR, TEST_COMPANY


def acc(name: str) -> str:
    return f"{name} - {TEST_ABBR}"


def ensure_customer(name="_Test PH Customer") -> str:
    if not frappe.db.exists("Customer", name):
        frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": name,
                "customer_type": "Company",
                "customer_group": "Commercial",
                "territory": "All Territories",
            }
        ).insert(ignore_permissions=True)
    return name


def ensure_supplier(name="_Test PH Supplier") -> str:
    if not frappe.db.exists("Supplier", name):
        frappe.get_doc(
            {
                "doctype": "Supplier",
                "supplier_name": name,
                "supplier_type": "Company",
                "supplier_group": "Services",
            }
        ).insert(ignore_permissions=True)
    return name


def ensure_service_item(code="_Test PH Service") -> str:
    if not frappe.db.exists("Item", code):
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": code,
                "item_name": code,
                "item_group": "Services",
                "stock_uom": "Nos",
                "is_stock_item": 0,
            }
        ).insert(ignore_permissions=True)
    return code


def make_sales_invoice(submit=True, rate=1000, **kwargs):
    si = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "company": TEST_COMPANY,
            "customer": ensure_customer(),
            "posting_date": today(),
            "due_date": today(),
            "debit_to": acc("Debtors"),
            "items": [
                {
                    "item_code": ensure_service_item(),
                    "qty": 1,
                    "rate": rate,
                    "income_account": acc("Sales"),
                    "cost_center": acc("Main"),
                }
            ],
            **kwargs,
        }
    ).insert()
    if submit:
        si.submit()
    return si


def make_journal_entry(submit=True, amount=500):
    je = frappe.get_doc(
        {
            "doctype": "Journal Entry",
            "company": TEST_COMPANY,
            "voucher_type": "Journal Entry",
            "posting_date": today(),
            "accounts": [
                {"account": acc("Cash"), "debit_in_account_currency": amount, "cost_center": acc("Main")},
                {"account": acc("Sales"), "credit_in_account_currency": amount, "cost_center": acc("Main")},
            ],
        }
    ).insert()
    if submit:
        je.submit()
    return je


def ensure_user(email: str, roles: list[str]) -> str:
    if not frappe.db.exists("User", email):
        user = frappe.get_doc(
            {"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
        )
        user.flags.ignore_permissions = True
        user.insert()
    user = frappe.get_doc("User", email)
    user.enabled = 1  # an earlier run may have left it deactivated (failed sign-ins, user limits)
    existing = {r.role for r in user.roles}
    for role in roles:
        if role not in existing:
            user.append("roles", {"role": role})
    user.flags.ignore_permissions = True
    user.save()
    return email


def ensure_stock_item(code="_Test PH Stock Item") -> str:
    if not frappe.db.exists("Item", code):
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": code,
                "item_name": code,
                "item_group": "Products",
                "stock_uom": "Nos",
                "is_stock_item": 1,
                "valuation_rate": 10,
            }
        ).insert(ignore_permissions=True)
    return code


def ensure_warehouse(name="Stores") -> str:
    full = acc(name)
    if not frappe.db.exists("Warehouse", full):
        frappe.get_doc({"doctype": "Warehouse", "warehouse_name": name, "company": TEST_COMPANY}).insert(
            ignore_permissions=True
        )
    return full


def ensure_supplier_profile(name, **fields) -> str:
    s = ensure_supplier(name)
    doc = frappe.get_doc("Supplier", s)
    for k, v in fields.items():
        doc.set(k, v)
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.clear_document_cache("Supplier", s)
    return s


def make_purchase_invoice(supplier, lines, submit=False, **kw):
    """lines: [(item_code, qty, rate, extra)]"""
    pi = frappe.get_doc(
        {
            "doctype": "Purchase Invoice",
            "company": TEST_COMPANY,
            "supplier": supplier,
            "posting_date": today(),
            "due_date": today(),
            "bill_no": kw.pop("bill_no", f"BILL-{frappe.generate_hash(length=6)}"),
            "bill_date": today(),
            "credit_to": acc("Creditors"),
            "items": [
                {"item_code": code, "qty": qty, "rate": rate, "expense_account": acc("Administrative Expenses"), "cost_center": acc("Main"), **extra}
                for code, qty, rate, extra in lines
            ],
            **kw,
        }
    ).insert()
    if submit:
        pi.submit()
    return pi
