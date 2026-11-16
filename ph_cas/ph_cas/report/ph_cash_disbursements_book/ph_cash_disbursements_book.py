"""Cash Disbursements Book: every payment out of cash or bank, with the
voucher or check number, payee, TIN, particulars, the cash credit and the
accounts debited (expense, payable, input VAT)."""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.books.common import cash_accounts, gl_rows, net_by_account, party_name, party_tin, tie_row, voucher_serial


def execute(filters=None):
    f = frappe._dict(filters or {})
    columns = [
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 95},
        {"fieldname": "reference", "label": _("Voucher / Check No."), "fieldtype": "Data", "width": 160},
        {"fieldname": "payee", "label": _("Paid to"), "fieldtype": "Data", "width": 200},
        {"fieldname": "tin", "label": _("TIN"), "fieldtype": "Data", "width": 130},
        {"fieldname": "particulars", "label": _("Particulars"), "fieldtype": "Data", "width": 220},
        {"fieldname": "cash_credit", "label": _("Cash / Bank (Cr)"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "debit_account", "label": _("Account debited"), "fieldtype": "Link", "options": "Account", "width": 220},
        {"fieldname": "debit", "label": _("Debit"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "other_credit_account", "label": _("Other account credited"), "fieldtype": "Link", "options": "Account", "width": 220},
        {"fieldname": "other_credit", "label": _("Other credit"), "fieldtype": "Currency", "width": 130},
    ]
    cash = cash_accounts(f.company)
    entries = gl_rows(f.company, f.from_date, f.to_date)
    by_voucher = {}
    for g in entries:
        by_voucher.setdefault((g.voucher_type, g.voucher_no, g.posting_date), []).append(g)
    cache, pcache, rows = {}, {}, []
    total_cash, total_debit, total_other = 0.0, 0.0, 0.0
    for (vt, vn, date), lines in sorted(by_voucher.items(), key=lambda kv: (kv[0][2], kv[0][1])):
        cash_cr = sum(flt(l.credit) for l in lines if l.account in cash)
        if cash_cr <= 0:
            continue
        party_line = next((l for l in lines if l.party), None)
        ref = voucher_serial(vt, vn, cache)
        if vt == "Payment Entry":
            chk = frappe.db.get_value("Payment Entry", vn, "reference_no")
            if chk:
                ref = f"{vn} / {chk}"
        netted = net_by_account(lines, skip=cash)
        debits = [l for l in netted if flt(l.debit) > 0]
        others = [l for l in netted if flt(l.credit) > 0]  # e.g. tax withheld on the payment
        for i in range(max(len(debits), len(others))):
            first = i == 0
            d = debits[i] if i < len(debits) else None
            o = others[i] if i < len(others) else None
            rows.append({
                "posting_date": date if first else None,
                "reference": ref if first else None,
                "payee": party_name(party_line.party_type, party_line.party, pcache) if (first and party_line) else None,
                "tin": party_tin(party_line.party_type, party_line.party, pcache) if (first and party_line) else None,
                "particulars": (lines[0].remarks or vt).replace("\n", " ")[:120] if first else None,
                "cash_credit": flt(cash_cr, 2) if first else None,
                "debit_account": d.account if d else None, "debit": flt(d.debit) if d else None,
                "other_credit_account": o.account if o else None, "other_credit": flt(o.credit) if o else None,
            })
            total_debit += flt(d.debit) if d else 0
            total_other += flt(o.credit) if o else 0
        total_cash += cash_cr
    rows.append({"reference": _("TOTAL"), "cash_credit": flt(total_cash, 2), "debit": flt(total_debit, 2), "other_credit": flt(total_other, 2), "is_total_row": 1})
    ledger_cash = frappe.db.sql(
        """select coalesce(sum(g.credit), 0) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
           where g.company = %s and g.is_cancelled = 0 and g.posting_date between %s and %s and a.account_type in ('Cash', 'Bank')""",
        (f.company, f.from_date, f.to_date),
    )[0][0]
    rows.append(tie_row(_("Tie-out of cash credits"), flt(total_cash, 2) == flt(ledger_cash, 2), f"ledger {flt(ledger_cash):,.2f}"))
    return columns, rows
