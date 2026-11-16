"""General Ledger: per account, opening balance, every posting with running
balance, closing balance; the closing balance is checked against the ledger."""

import frappe
from frappe import _
from frappe.utils import add_days, flt

from ph_cas.books.common import gl_rows, party_name, voucher_kind, voucher_serial


def opening(company, account, start) -> float:
    row = frappe.db.sql(
        """select coalesce(sum(debit) - sum(credit), 0) from `tabGL Entry`
           where company = %s and account = %s and is_cancelled = 0 and posting_date < %s""",
        (company, account, start),
    )[0][0]
    return flt(row, 2)


def execute(filters=None):
    f = frappe._dict(filters or {})
    columns = [
        {"fieldname": "account", "label": _("Account"), "fieldtype": "Link", "options": "Account", "width": 240},
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 95},
        {"fieldname": "reference", "label": _("Reference"), "fieldtype": "Data", "width": 150},
        {"fieldname": "document", "label": _("Document"), "fieldtype": "Data", "width": 130},
        {"fieldname": "particulars", "label": _("Particulars"), "fieldtype": "Data", "width": 260},
        {"fieldname": "debit", "label": _("Debit"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "credit", "label": _("Credit"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "balance", "label": _("Balance"), "fieldtype": "Currency", "width": 140},
    ]
    extra = " and g.account = %(account)s" if f.get("account") else ""
    entries = gl_rows(f.company, f.from_date, f.to_date, extra, {"account": f.get("account")})
    accounts = sorted({g.account for g in entries} | ({f.account} if f.get("account") else set()))
    cache, pcache, rows = {}, {}, []
    for account in accounts:
        bal = opening(f.company, account, f.from_date)
        rows.append({"account": account, "particulars": _("Opening balance"), "balance": bal, "is_opening": 1})
        for g in [e for e in entries if e.account == account]:
            bal = flt(bal + flt(g.debit) - flt(g.credit), 2)
            rows.append({"account": account, "posting_date": g.posting_date, "reference": voucher_serial(g.voucher_type, g.voucher_no, cache), "document": voucher_kind(g.voucher_type, g.voucher_no, cache), "particulars": " ".join(x for x in [party_name(g.party_type, g.party, pcache), (g.remarks or "").replace("\n", " ")[:120]] if x), "debit": flt(g.debit), "credit": flt(g.credit), "balance": bal})
        ledger_close = flt(opening(f.company, account, add_days(f.to_date, 1)), 2)
        rows.append({"account": account, "particulars": _("Closing balance") + (" " + _("(ties)") if ledger_close == bal else " " + _("(DOES NOT TIE)")), "balance": bal, "is_closing": 1})
    return columns, rows
