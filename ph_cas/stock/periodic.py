"""B69 (QA pass 4, D7 revised): the year-end inventory adjustment of a periodic company.

Under the periodic method (ph_cas.controls.dates, Company "Inventory method"), purchases of stock go
to cost of sales and the inventory account keeps last year's ending balance. After the year-end
count (a Stock Reconciliation on the count day), this posts the difference between the counted
stock value and the inventory account to cost of sales, so that

    cost of sales = beginning inventory + purchases - ending inventory

and the income tax returns, which read cost of sales from the ledger, carry the right figure.
Run it again after a later count or correction: it posts only the remaining difference.

A perpetual company needs none of this: its count (Stock Reconciliation) posts the adjustment
itself."""

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from ph_cas.controls.dates import REASON_FIELD

REMARK = "Year-end inventory adjustment"


def inventory_account(company: str) -> str:
    c = frappe.get_cached_doc("Company", company)
    acc = c.get("default_inventory_account") or frappe.db.get_value("Account", {"company": company, "account_type": "Stock", "is_group": 0}, "name")
    if not acc:
        frappe.throw(_("{0} has no inventory (Stock) account.").format(company))
    return acc


def counted_value(company: str, as_of) -> float:
    """The stock value at the end of as_of, from the stock ledger (the count's valuation)."""
    return flt(frappe.db.sql(
        """select sum(stock_value_difference) from `tabStock Ledger Entry`
           where company = %s and is_cancelled = 0 and posting_date <= %s""", (company, as_of))[0][0], 2)


def book_value(company: str, account: str, as_of) -> float:
    return flt(frappe.db.sql(
        """select sum(debit) - sum(credit) from `tabGL Entry`
           where company = %s and account = %s and is_cancelled = 0 and posting_date <= %s""", (company, account, as_of))[0][0], 2)


@frappe.whitelist()
def preview(company: str, as_of: str | None = None) -> dict:
    as_of = as_of or today()
    acc = inventory_account(company)
    ending, book = counted_value(company, as_of), book_value(company, acc, as_of)
    return {"company": company, "as_of": str(as_of), "inventory_account": acc, "counted": ending, "books": book, "adjustment": flt(ending - book, 2)}


@frappe.whitelist()
def post_adjustment(company: str, as_of: str | None = None, reason: str | None = None) -> dict:
    """Post the year-end adjustment as a Journal Entry dated as_of (the count day)."""
    frappe.has_permission("Journal Entry", "create", throw=True)
    if frappe.get_cached_value("Company", company, "enable_perpetual_inventory"):
        frappe.throw(_("{0} uses the perpetual method: the count (Stock Reconciliation) already posts the adjustment.").format(company))
    p = preview(company, as_of)
    diff = p["adjustment"]
    if abs(diff) < 0.005:
        return {**p, "journal_entry": None}
    cogs = frappe.get_cached_value("Company", company, "default_expense_account") or frappe.db.get_value(
        "Account", {"company": company, "account_type": "Cost of Goods Sold", "is_group": 0}, "name")
    cc = frappe.get_cached_value("Company", company, "cost_center")
    inv, amt = p["inventory_account"], abs(diff)
    debit, credit = (inv, cogs) if diff > 0 else (cogs, inv)
    je = frappe.get_doc({
        "doctype": "Journal Entry", "company": company, "voucher_type": "Journal Entry", "posting_date": p["as_of"],
        "user_remark": f"{REMARK} as of {p['as_of']}: counted {p['counted']:,.2f}, books {p['books']:,.2f}",
        "accounts": [
            {"account": debit, "debit_in_account_currency": amt, "cost_center": cc},
            {"account": credit, "credit_in_account_currency": amt, "cost_center": cc},
        ],
    })
    if getdate(p["as_of"]) < getdate(today()):
        je.set(REASON_FIELD, reason or f"{REMARK} for the count of {p['as_of']}")
    je.insert()
    je.submit()
    return {**p, "journal_entry": je.name}
