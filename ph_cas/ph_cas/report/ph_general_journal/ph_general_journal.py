"""General Journal: every posting in date order, one line per ledger entry
(date, reference, particulars, account, debit, credit), with a tie-out line."""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.books.common import gl_rows, party_name, tie_out, tie_row, voucher_kind, voucher_serial
from ph_cas.books.common import check_company


def execute(filters=None):
    f = frappe._dict(filters or {})
    check_company(f.get("company"))
    columns = [
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 95},
        {"fieldname": "reference", "label": _("Reference"), "fieldtype": "Data", "width": 150},
        {"fieldname": "voucher_type", "label": _("Document"), "fieldtype": "Data", "width": 120},
        {"fieldname": "particulars", "label": _("Particulars"), "fieldtype": "Data", "width": 260},
        {"fieldname": "account", "label": _("Account"), "fieldtype": "Link", "options": "Account", "width": 220},
        {"fieldname": "debit", "label": _("Debit"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "credit", "label": _("Credit"), "fieldtype": "Currency", "width": 130},
    ]
    cache, pcache = {}, {}
    rows, td, tc = [], 0.0, 0.0
    for g in gl_rows(f.company, f.from_date, f.to_date):
        rows.append({
            "posting_date": g.posting_date,
            "reference": voucher_serial(g.voucher_type, g.voucher_no, cache),
            "voucher_type": voucher_kind(g.voucher_type, g.voucher_no, cache),
            "particulars": " ".join(x for x in [party_name(g.party_type, g.party, pcache), (g.remarks or "").replace("\n", " ")[:120]] if x),
            "account": g.account,
            "debit": flt(g.debit), "credit": flt(g.credit),
        })
        td += flt(g.debit)
        tc += flt(g.credit)
    rows.append({"reference": _("TOTAL"), "debit": flt(td, 2), "credit": flt(tc, 2), "is_total_row": 1})
    t = tie_out(td, tc, f.company, f.from_date, f.to_date)
    rows.append(tie_row(_("Tie-out"), t["ties"], f"ledger {t['ledger_debit']:,.2f} / {t['ledger_credit']:,.2f}"))
    return columns, rows
