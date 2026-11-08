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
