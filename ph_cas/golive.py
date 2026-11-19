"""B71: go-live and opening balances (after ECOUNT's starting balance and cut-over rule).

A company records the day it starts using Sentire Ledger (Company > Go-live date). Everything the
old books still carry goes in dated the day before, the cut-over day:

- account balances, and what each customer owes and each supplier is owed, in an opening Journal
  Entry (Entry Type "Opening Entry"; Is Opening "Yes"; party rows on Debtors and Creditors, each
  with the old invoice or bill number in its remark). Collections and payments are then matched
  to those rows like any open item.
- the stock on hand in an opening stock count (Stock Reconciliation, purpose "Opening Stock").

Those two, and only those, may carry the cut-over day without the manager's reason for an earlier
date (ph_cas.controls.dates). Opening invoices and bills (ERPNext's Opening Invoice Creation Tool)
are refused: an old invoice is not a new BIR invoice, so it must not take a BIR serial, carry VAT
again or enter the sales journal and the returns.

go_live_checklist() reports what is done and what is missing, for the Company's Go-live checklist.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import add_days, flt, getdate

GO_LIVE = "ph_go_live_date"
OPENING_PURPOSE = "Opening Stock"


def setup():
    create_custom_fields({"Company": [{
        "fieldname": GO_LIVE, "fieldtype": "Date", "label": "Go-live date",
        "insert_after": "ph_inventory_method",
        "description": "The first day the company's books are kept in Sentire Ledger. Opening balances and the opening stock count are dated the day before (the cut-over day).",
    }]}, ignore_validate=True, update=True)


def cutover(company: str):
    go = frappe.get_cached_value("Company", company, GO_LIVE)
    return add_days(go, -1) if go else None


def is_opening(doc) -> bool:
    if doc.doctype == "Stock Reconciliation":
        return doc.get("purpose") == OPENING_PURPOSE
    return (doc.get("is_opening") or "No") == "Yes"


def check_opening(doc) -> bool:
    """Called from validate_posting_date. Returns True when the document is an opening entry dated
    the cut-over day (the date rules are then satisfied); refuses opening documents that break the
    cut-over rule. Returns False for ordinary documents."""
    if doc.doctype in ("Sales Invoice", "Purchase Invoice") and is_opening(doc):
        frappe.throw(
            _("Old unpaid invoices and bills are not entered as {0}s: an old invoice is not a new BIR invoice. Enter what each customer still owes, or each supplier is still owed, as party rows in an opening Journal Entry dated the day before go-live (Company > Go-live checklist).").format(_(doc.doctype)),
            frappe.ValidationError,
        )
    if doc.doctype not in ("Journal Entry", "Stock Reconciliation") or not is_opening(doc):
        return False
    day = cutover(doc.company)
    if not day:
        frappe.throw(
            _("Set {0}'s go-live date first (Company > Go-live date). Opening balances are dated the day before it.").format(doc.company),
            frappe.ValidationError,
        )
    if getdate(doc.posting_date) != getdate(day):
        frappe.throw(
            _("{0}: opening entries are dated the day before go-live, {1}.").format(_(doc.doctype), frappe.format(day, "Date")),
            frappe.ValidationError,
        )
    return True


# ---- the checklist -------------------------------------------------------------------------------
COR_FIELDS = [("tax_id", "TIN"), ("ph_rdo", "RDO"), ("ph_registered_name", "registered name"), ("ph_registered_address", "registered address"),
              ("ph_vat_status", "VAT status"), ("ph_taxpayer_type", "taxpayer type")]


def _item(key, label, status, detail, route=None):
    return {"key": key, "label": label, "status": status, "detail": detail, "route": route}


@frappe.whitelist()
def go_live_checklist(company: str) -> list[dict]:
    frappe.has_permission("Company", "read", company, throw=True)
    c = frappe.get_doc("Company", company)
    out = []

    missing = [label for f, label in COR_FIELDS if not (c.get(f) or "").strip()]
    out.append(_item("cor", _("COR details on the Company"), "missing" if missing else "done",
                     _("Missing: {0}").format(", ".join(missing)) if missing else _("TIN, RDO, registered name and address, VAT status, taxpayer type"), f"/app/company/{company}"))

    series = frappe.get_all("BIR Series", filters={"company": company}, pluck="document_type")
    out.append(_item("setup", _("Philippine setup (accounts, mapping, BIR Series)"), "done" if "Sales Invoice" in series else "missing",
                     _("{0} BIR Series").format(len(series)) if series else _("Run Company > Sentire Ledger > Set up Philippine company"), f"/app/company/{company}"))

    drafts = frappe.db.count("PH Tax Rule", {"status": "draft"}) if frappe.db.exists("DocType", "PH Tax Rule") and frappe.get_meta("PH Tax Rule").has_field("status") else 0
    out.append(_item("rules", _("Tax rules confirmed"), "missing" if drafts else "done",
                     _("{0} draft rule(s) to confirm").format(drafts) if drafts else _("All rules confirmed"), "/app/ph-tax-rule"))

    go = c.get(GO_LIVE)
    out.append(_item("go_live", _("Go-live date"), "done" if go else "missing",
                     _("Live from {0}; opening entries dated {1}").format(frappe.format(go, "Date"), frappe.format(add_days(go, -1), "Date")) if go else _("Set it on the Company"),
                     f"/app/company/{company}"))

    method = c.get("ph_inventory_method") or "Periodic"
    moved = frappe.db.exists("Stock Ledger Entry", {"company": company, "is_cancelled": 0})
    out.append(_item("inventory", _("Inventory method"), "done",
                     _("{0}{1}").format(method, _(" (locked: stock has moved)") if moved else _(" (can still change)")), f"/app/company/{company}"))

    banks = frappe.db.count("Bank Account", {"company": company}) if frappe.db.exists("DocType", "Bank Account") else 0
    out.append(_item("bank", _("Bank account"), "done" if banks else "optional",
                     _("{0} bank account(s)").format(banks) if banks else _("None yet; add the account customers pay into"), "/app/bank-account/new"))
    # B76: the company credit card the Philippine setup adds (a liability, paid like a bank account)
    from ph_cas.setup.chart import CARD_ACCOUNT

    card = frappe.db.get_value("Account", {"company": company, "account_name": CARD_ACCOUNT, "root_type": "Liability"}, "name")
    out.append(_item("card", _("Credit card"), "done" if card else "optional",
                     _("{0}: pick it under Paid from when you record an expense paid by card").format(card) if card else _("Run Set up Philippine company to add it"),
                     f"/app/account/{card}" if card else f"/app/company/{company}"))

    with_profile = frappe.db.sql("select count(distinct parent) from `tabUser Role Profile` where parenttype = 'User'")[0][0] if frappe.db.table_exists("User Role Profile") else 0
    out.append(_item("users", _("Users with a role set"), "done" if with_profile else "optional",
                     _("{0} user(s) with Owner, Bookkeeper or Cashier").format(with_profile) if with_profile else _("Give each user a role set (User > Role Profiles)"), "/app/user"))

    day = add_days(go, -1) if go else None
    if day:
        jes = frappe.get_all("Journal Entry", filters={"company": company, "docstatus": 1, "is_opening": "Yes"}, pluck="name")
        tb = frappe.db.sql("""select coalesce(sum(debit), 0), coalesce(sum(credit), 0) from `tabGL Entry`
                              where company = %s and is_cancelled = 0 and posting_date <= %s""", (company, day))[0]
        temp = _temporary_opening_balance(company, day)
        status = "done" if jes and abs(flt(tb[0]) - flt(tb[1])) < 0.01 and abs(temp) < 0.01 else "missing"
        detail = _("{0} opening entr(ies); debits {1:,.2f} = credits {2:,.2f}").format(len(jes), flt(tb[0]), flt(tb[1])) if jes else _("No opening Journal Entry dated {0} yet").format(frappe.format(day, "Date"))
        if jes and abs(temp) >= 0.01:
            detail += _("; Temporary Opening still holds {0:,.2f}").format(temp)
        out.append(_item("balances", _("Opening account balances"), status, detail, "/app/journal-entry/new"))

        parties = frappe.db.sql("""select a.party_type, count(distinct a.party) from `tabJournal Entry Account` a join `tabJournal Entry` j on j.name = a.parent
                                   where j.company = %s and j.docstatus = 1 and j.is_opening = 'Yes' and ifnull(a.party, '') != '' group by a.party_type""", company)
        counts = {p: n for p, n in parties}
        out.append(_item("open_items", _("Open invoices and bills from the old books"), "done" if counts else "optional",
                         _("{0} customer(s), {1} supplier(s) with opening balances").format(counts.get("Customer", 0), counts.get("Supplier", 0)) if counts
                         else _("Party rows on Debtors and Creditors in the opening Journal Entry"), "/app/journal-entry/new"))

        stocked = frappe.db.exists("Item", {"is_stock_item": 1, "disabled": 0})
        if stocked:
            if method == "Perpetual":
                done = frappe.db.exists("Stock Reconciliation", {"company": company, "docstatus": 1, "purpose": OPENING_PURPOSE})
                detail = _("Opening stock count posted") if done else _("Post an opening stock count dated {0}").format(frappe.format(day, "Date"))
            else:
                from ph_cas.stock.periodic import book_value, inventory_account

                inv = book_value(company, inventory_account(company), day)
                done = frappe.db.exists("Stock Reconciliation", {"company": company, "docstatus": 1, "purpose": OPENING_PURPOSE}) and inv
                detail = _("Opening stock count posted; inventory account {0:,.2f}").format(inv) if done else _(
                    "Post an opening stock count dated {0}, and put its value on the inventory account in the opening Journal Entry").format(frappe.format(day, "Date"))
            out.append(_item("stock", _("Opening stock"), "done" if done else "missing", detail, "/app/stock-reconciliation/new"))
    return out


def _temporary_opening_balance(company, day) -> float:
    acc = frappe.db.get_value("Account", {"company": company, "account_type": "Temporary", "is_group": 0}, "name")
    if not acc:
        return 0.0
    return flt(frappe.db.sql("""select coalesce(sum(debit) - sum(credit), 0) from `tabGL Entry`
                                where company = %s and account = %s and is_cancelled = 0 and posting_date <= %s""", (company, acc, day))[0][0], 2)
