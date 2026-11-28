"""B72: Record an expense (after ECOUNT's payment journal / Fast Entry).

One screen for a bill that is already paid: who was paid, what for, the amount on the receipt
and where the money came from. It posts an ordinary Purchase Invoice marked paid (Is Paid), so the
tax engine works out the input VAT, the expanded withholding (and the 2307 the supplier is owed)
from the supplier's profile and the item, and the expense enters the purchase journal, the cash
disbursements book, the 1601-EQ, the 2550Q and the income tax returns like any other bill.

The amount is what the receipt shows. For a VAT supplier on a VATable line it includes VAT: the net
is worked back from the purchase VAT rule of the day. Withholding is on the net, so the cash paid is
net + VAT - EWT.

preview_expense() returns the figures without posting; record_expense() posts. Both follow the
user's own permissions: a Cashier may not post bills (ph_cas.setup.roles.cashier_limit).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from ph_cas.tax.rules import resolve


def _build(company, supplier, amount, description, expense_account=None, item_code=None, paid_from=None, receipt_no=None, receipt_date=None, vat_class=None, mode_of_payment=None):
    amount = flt(amount, 2)
    if amount <= 0:
        frappe.throw(_("Enter the amount on the receipt."))
    c = frappe.get_cached_doc("Company", company)
    s = frappe.get_cached_doc("Supplier", supplier)
    cls = vat_class or (frappe.get_cached_value("Item", item_code, "ph_vat_class") if item_code else None) or "VATable"
    vat_supplier = (s.get("ph_vat_status") or "Non-VAT") == "VAT" and not s.get("ph_is_nonresident_dsp")
    net = amount
    if vat_supplier and cls in ("VATable", "Government"):
        rate = flt(resolve("vat", getdate(today()), side="purchase").rate)
        net = flt(amount / (1 + rate / 100), 2)
    # the expense account is chosen, or comes from the item; never the company's default, which is
    # cost of goods sold (a fee or a fare there would distort gross profit on the income tax return)
    account = expense_account or (frappe.get_cached_value("Item Default", {"parent": item_code, "company": company}, "expense_account") if item_code else None)
    if not account:
        frappe.throw(_("Choose the expense account (or an item that has one for {0}).").format(company))
    line = {"qty": 1, "rate": net, "expense_account": account, "cost_center": c.cost_center, "ph_vat_class": cls,
            "description": description or (frappe.get_cached_value("Item", item_code, "item_name") if item_code else _("Expense"))}
    if item_code:
        line["item_code"] = item_code
    else:
        line["item_name"] = (description or _("Expense"))[:140]
        line["uom"] = "Nos"
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice", "company": company, "supplier": supplier, "posting_date": today(),
        "bill_no": receipt_no, "bill_date": receipt_date or today(), "credit_to": c.default_payable_account,
        "is_paid": 1, "cash_bank_account": paid_from or _mode_account(mode_of_payment, company) or c.default_cash_account, "mode_of_payment": mode_of_payment,
        "remarks": description, "items": [line],
    })
    return pi


def _mode_account(mode, company):
    """B76: paying by card (or any mode) without choosing Paid from uses the mode's account."""
    if not mode:
        return None
    return frappe.db.get_value("Mode of Payment Account", {"parent": mode, "company": company}, "default_account")


def _figures(pi) -> dict:
    return {
        "net": flt(pi.net_total, 2),
        "vat": flt(sum(flt(pi.get(f"ph_input_vat_{k}")) for k in ("goods", "services", "capital")) + flt(pi.get("ph_vat_cost")), 2),
        "ewt": flt(pi.get("ph_ewt_amount"), 2), "ewt_atc": pi.get("ph_ewt_atc"),
        "paid": flt(pi.get("rounded_total") or pi.grand_total, 2),
    }


@frappe.whitelist()
def preview_expense(**kwargs) -> dict:
    kwargs.pop("cmd", None)
    frappe.has_permission("Purchase Invoice", "create", throw=True)
    from ph_cas.setup.roles import cashier_limit

    if not cashier_limit("Purchase Invoice", "create"):  # B97: Staff reads bills, posts none
        frappe.throw(_("Your role may not post bills or expenses."), frappe.PermissionError)
    pi = _build(**kwargs)
    pi.set_missing_values()
    pi.run_method("before_validate")
    pi.calculate_taxes_and_totals()
    return _figures(pi)


@frappe.whitelist()
def record_expense(**kwargs) -> dict:
    kwargs.pop("cmd", None)
    frappe.has_permission("Purchase Invoice", "create", throw=True)
    from ph_cas.setup.roles import cashier_limit

    if not cashier_limit("Purchase Invoice", "create"):  # B97: Staff reads bills, posts none
        frappe.throw(_("Your role may not post bills or expenses."), frappe.PermissionError)
    pi = _build(**kwargs)
    pi.insert()
    pi.paid_amount = pi.base_paid_amount = flt(pi.get("rounded_total") or pi.grand_total, 2)
    pi.save()
    pi.submit()
    return {"purchase_invoice": pi.name, **_figures(pi)}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def paid_from_query(doctype, txt, searchfield, start, page_len, filters):
    """Record an expense > Paid from: the company's cash and bank accounts and its credit card."""
    from ph_cas.setup.chart import CARD_ACCOUNT

    company = (filters or {}).get("company")
    return frappe.db.sql(
        """select name, account_name from `tabAccount`
           where company = %(company)s and is_group = 0 and disabled = 0 and name like %(txt)s
             and ((account_type in ('Cash', 'Bank') and root_type = 'Asset') or (account_name = %(card)s and root_type = 'Liability'))
           order by name limit %(start)s, %(page_len)s""",
        {"company": company, "txt": f"%{txt}%", "card": CARD_ACCOUNT, "start": int(start), "page_len": int(page_len)})
