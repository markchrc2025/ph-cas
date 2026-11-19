"""B74: the daily cash position (after ECOUNT's daily cash and bank report).

For each cash and bank account of the company: the balance at the start of the day, what came in
and what went out that day, and the balance at the end of it, with the total. The closing total is
the cash and bank balance in the general ledger at the end of the day."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from ph_cas.books.common import cash_accounts


@frappe.whitelist()
def cash_position(company: str, day: str | None = None) -> dict:
    frappe.has_permission("GL Entry", "read", throw=True)
    # B77: another company's cash is not shown to a user kept to their own (User Permission)
    frappe.has_permission("Company", "read", company, throw=True)
    day = getdate(day or today())
    accounts = sorted(cash_accounts(company))
    rows = []
    if accounts:
        data = frappe.db.sql(
            """select account,
                      coalesce(sum(case when posting_date < %(day)s then debit - credit end), 0),
                      coalesce(sum(case when posting_date = %(day)s then debit end), 0),
                      coalesce(sum(case when posting_date = %(day)s then credit end), 0),
                      count(distinct case when posting_date = %(day)s then voucher_no end)
               from `tabGL Entry` where company = %(company)s and is_cancelled = 0 and posting_date <= %(day)s and account in %(accounts)s
               group by account""", {"company": company, "day": day, "accounts": accounts})
        found = {a: (flt(o, 2), flt(i, 2), flt(x, 2), n) for a, o, i, x, n in data}
        for a in accounts:
            o, i, x, n = found.get(a, (0.0, 0.0, 0.0, 0))
            rows.append({"account": a, "account_type": frappe.get_cached_value("Account", a, "account_type"), "opening": o, "received": i, "paid": x,
                         "closing": flt(o + i - x, 2), "entries": n})
    total = {k: flt(sum(r[k] for r in rows), 2) for k in ("opening", "received", "paid", "closing")}
    return {"company": company, "day": str(day), "accounts": rows, "total": total}
