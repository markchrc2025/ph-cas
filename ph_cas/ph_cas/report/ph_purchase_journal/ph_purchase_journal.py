"""Purchase Journal: date, supplier invoice number, supplier TIN and name,
purchases by input VAT kind, purchases without input VAT, input VAT, EWT by
ATC, reverse-charge VAT, total; one line per bill."""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.books.common import tie_row
from ph_cas.setup.chart import account_for


def execute(filters=None):
    f = frappe._dict(filters or {})
    columns = [
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 95},
        {"fieldname": "bill_no", "label": _("Supplier Invoice No."), "fieldtype": "Data", "width": 140},
        {"fieldname": "tin", "label": _("Supplier TIN"), "fieldtype": "Data", "width": 130},
        {"fieldname": "supplier_name", "label": _("Supplier"), "fieldtype": "Data", "width": 200},
        {"fieldname": "goods", "label": _("Goods (net)"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "services", "label": _("Services (net)"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "capital", "label": _("Capital goods (net)"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "ph_exempt_purchases", "label": _("No input VAT"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "input_vat", "label": _("Input VAT"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "ph_ewt_atc", "label": _("EWT ATC"), "fieldtype": "Data", "width": 80},
        {"fieldname": "ph_ewt_amount", "label": _("EWT"), "fieldtype": "Currency", "width": 100},
        {"fieldname": "ph_rc_vat", "label": _("Reverse-charge VAT"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "grand_total", "label": _("Amount payable"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "name", "label": _("Document"), "fieldtype": "Link", "options": "Purchase Invoice", "width": 160},
    ]
    from ph_cas.tax.rules import resolve

    rate = flt(resolve("vat", f.to_date, side="purchase").rate) or 12
    bills = frappe.get_all(
        "Purchase Invoice",
        filters={"company": f.company, "docstatus": 1, "posting_date": ("between", [f.from_date, f.to_date])},
        fields=["name", "posting_date", "bill_no", "supplier", "supplier_name", "ph_input_vat_goods", "ph_input_vat_services", "ph_input_vat_capital", "ph_exempt_purchases", "ph_ewt_atc", "ph_ewt_amount", "ph_rc_vat", "ph_rc_base", "grand_total", "ph_vat_cost"],
        order_by="posting_date, name",
    )
    rows, tot = [], {"goods": 0, "services": 0, "capital": 0, "ph_exempt_purchases": 0, "input_vat": 0, "ph_ewt_amount": 0, "ph_rc_vat": 0, "grand_total": 0}
    for pi in bills:
        tin, branch = frappe.db.get_value("Supplier", pi.supplier, ["ph_tin", "ph_branch_code"]) or (None, None)
        goods = flt(pi.ph_input_vat_goods) * 100 / rate
        services = flt(pi.ph_input_vat_services) * 100 / rate
        capital = flt(pi.ph_input_vat_capital) * 100 / rate
        if flt(pi.ph_vat_cost):  # Non-VAT buyer: VAT is cost, purchases are shown in services (net) column
            services += flt(pi.ph_vat_cost) * 100 / rate
        exempt = flt(pi.ph_exempt_purchases) + (flt(pi.ph_rc_base) if pi.ph_rc_vat else 0)
        row = {"posting_date": pi.posting_date, "bill_no": pi.bill_no, "name": pi.name, "tin": f"{tin}-{branch or '00000'}" if tin else "", "supplier_name": pi.supplier_name,
               "goods": flt(goods, 2), "services": flt(services, 2), "capital": flt(capital, 2), "ph_exempt_purchases": flt(exempt, 2),
               "input_vat": flt(flt(pi.ph_input_vat_goods) + flt(pi.ph_input_vat_services) + flt(pi.ph_input_vat_capital), 2),
               "ph_ewt_atc": pi.ph_ewt_atc, "ph_ewt_amount": flt(pi.ph_ewt_amount), "ph_rc_vat": flt(pi.ph_rc_vat), "grand_total": flt(pi.grand_total)}
        for k in tot:
            tot[k] += row[k]
        rows.append(row)
    rows.append({"bill_no": _("TOTAL"), **{k: flt(v, 2) for k, v in tot.items()}, "is_total_row": 1})
    ledger_ewt = frappe.db.sql(
        """select coalesce(sum(credit) - sum(debit), 0) from `tabGL Entry`
           where company = %s and is_cancelled = 0 and account = %s and voucher_type = 'Purchase Invoice' and posting_date between %s and %s""",
        (f.company, account_for(f.company, "ewt_payable"), f.from_date, f.to_date),
    )[0][0]
    rows.append(tie_row(_("Tie-out of EWT withheld on bills"), flt(tot["ph_ewt_amount"], 2) == flt(ledger_ewt, 2), f"ledger {flt(ledger_ewt):,.2f}"))
    return columns, rows
