"""Cash Receipts Book: every receipt of cash or bank, with the receipt number
(Collection Receipt serial), payor, TIN, particulars, the cash debit and the
accounts credited."""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.books.common import cash_accounts, gl_rows, party_name, party_tin, tie_row, voucher_serial


def execute(filters=None):
    f = frappe._dict(filters or {})
    columns = [
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 95},
        {"fieldname": "reference", "label": _("Receipt No."), "fieldtype": "Data", "width": 140},
        {"fieldname": "payor", "label": _("Received from"), "fieldtype": "Data", "width": 200},
        {"fieldname": "tin", "label": _("TIN"), "fieldtype": "Data", "width": 130},
        {"fieldname": "particulars", "label": _("Particulars"), "fieldtype": "Data", "width": 220},
        {"fieldname": "cash_debit", "label": _("Cash / Bank (Dr)"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "credit_account", "label": _("Account credited"), "fieldtype": "Link", "options": "Account", "width": 220},
        {"fieldname": "credit", "label": _("Credit"), "fieldtype": "Currency", "width": 130},
    ]
    cash = cash_accounts(f.company)
    entries = gl_rows(f.company, f.from_date, f.to_date)
    by_voucher = {}
    for g in entries:
        by_voucher.setdefault((g.voucher_type, g.voucher_no, g.posting_date), []).append(g)
    cache, pcache, rows = {}, {}, []
    total_cash, total_credit = 0.0, 0.0
    for (vt, vn, date), lines in sorted(by_voucher.items(), key=lambda kv: (kv[0][2], kv[0][1])):
        cash_dr = sum(flt(l.debit) for l in lines if l.account in cash)
        if cash_dr <= 0:
            continue
        party_line = next((l for l in lines if l.party), None)
        first = True
        for l in lines:
            if l.account in cash or flt(l.credit) <= 0:
                continue
            rows.append({
                "posting_date": date if first else None,
                "reference": voucher_serial(vt, vn, cache) if first else None,
                "payor": party_name(party_line.party_type, party_line.party, pcache) if (first and party_line) else None,
                "tin": party_tin(party_line.party_type, party_line.party, pcache) if (first and party_line) else None,
                "particulars": (lines[0].remarks or vt).replace("\n", " ")[:120] if first else None,
                "cash_debit": flt(cash_dr, 2) if first else None,
                "credit_account": l.account, "credit": flt(l.credit),
            })
            total_credit += flt(l.credit)
            first = False
        total_cash += cash_dr
    rows.append({"reference": _("TOTAL"), "cash_debit": flt(total_cash, 2), "credit": flt(total_credit, 2), "is_total_row": 1})
    ledger_cash = frappe.db.sql(
        """select coalesce(sum(g.debit), 0) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
           where g.company = %s and g.is_cancelled = 0 and g.posting_date between %s and %s and a.account_type in ('Cash', 'Bank')""",
        (f.company, f.from_date, f.to_date),
    )[0][0]
    rows.append(tie_row(_("Tie-out of cash debits"), flt(total_cash, 2) == flt(ledger_cash, 2), f"ledger {flt(ledger_cash):,.2f}"))
    return columns, rows
