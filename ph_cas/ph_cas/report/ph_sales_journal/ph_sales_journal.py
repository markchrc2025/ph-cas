"""Sales Journal (RR 9-2009): date, customer TIN, name, address, description,
document number, VATable, exempt, zero-rated, output VAT, withholding, total;
one line per invoice, credit notes negative. Totals tie to the invoices'
stored buckets and to the output VAT credited in the ledger."""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.books.common import tie_row
from ph_cas.setup.chart import account_for

COLS = ["ph_vatable_sales", "ph_exempt_sales", "ph_zero_rated_sales", "ph_vat_amount", "ph_wht_total", "grand_total"]


def execute(filters=None):
    f = frappe._dict(filters or {})
    columns = [
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 95},
        {"fieldname": "bir_serial", "label": _("Invoice No."), "fieldtype": "Data", "width": 110},
        {"fieldname": "doc_type", "label": _("Type"), "fieldtype": "Data", "width": 90},
        {"fieldname": "tin", "label": _("Customer TIN"), "fieldtype": "Data", "width": 130},
        {"fieldname": "customer_name", "label": _("Customer"), "fieldtype": "Data", "width": 200},
        {"fieldname": "address", "label": _("Address"), "fieldtype": "Data", "width": 200},
        {"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 200},
        {"fieldname": "ph_vatable_sales", "label": _("VATable"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "ph_exempt_sales", "label": _("Exempt"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "ph_zero_rated_sales", "label": _("Zero-rated"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "ph_vat_amount", "label": _("Output VAT"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "ph_wht_total", "label": _("Withheld by customer"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "grand_total", "label": _("Total"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "name", "label": _("Document"), "fieldtype": "Link", "options": "Sales Invoice", "width": 160},
    ]
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"company": f.company, "docstatus": 1, "posting_date": ("between", [f.from_date, f.to_date])},
        fields=["name", "posting_date", "bir_serial", "customer", "customer_name", "is_return", "is_debit_note", "address_display", "ph_pt_base"] + COLS,
        order_by="posting_date, bir_serial, name",
    )
    totals = {c: 0.0 for c in COLS}
    rows = []
    for si in invoices:
        tin, branch, l1, l2 = frappe.db.get_value("Customer", si.customer, ["ph_tin", "ph_branch_code", "ph_address_line1", "ph_address_line2"]) or (None, None, None, None)
        items = frappe.get_all("Sales Invoice Item", filters={"parent": si.name}, fields=["item_name"], limit=3)
        desc = ", ".join(i.item_name for i in items)
        row = {
            "posting_date": si.posting_date, "bir_serial": si.bir_serial, "name": si.name,
            "doc_type": "Credit Note" if si.is_return else ("Debit Note" if si.is_debit_note else "Invoice"),
            "tin": f"{tin}-{branch or '00000'}" if tin else "", "customer_name": si.customer_name,
            "address": ", ".join(p for p in [l1, l2] if p) or frappe.utils.strip_html(si.address_display or "").replace("\n", ", "),
            "description": desc[:120],
        }
        for c in COLS:
            v = flt(si.get(c))
            if c == "ph_vatable_sales" and not v and flt(si.ph_pt_base):
                v = flt(si.ph_pt_base)  # Non-VAT seller: sales subject to percentage tax in the VATable column
            row[c] = v
            totals[c] += v
        rows.append(row)
    rows.append({"bir_serial": _("TOTAL"), **{c: flt(v, 2) for c, v in totals.items()}, "is_total_row": 1})
    ledger_vat = frappe.db.sql(
        """select coalesce(sum(credit) - sum(debit), 0) from `tabGL Entry`
           where company = %s and is_cancelled = 0 and account = %s and voucher_type = 'Sales Invoice' and posting_date between %s and %s""",
        (f.company, account_for(f.company, "output_vat"), f.from_date, f.to_date),
    )[0][0]
    rows.append(tie_row(_("Tie-out of output VAT"), flt(totals["ph_vat_amount"], 2) == flt(ledger_vat, 2), f"ledger {flt(ledger_vat):,.2f}"))
    return columns, rows
