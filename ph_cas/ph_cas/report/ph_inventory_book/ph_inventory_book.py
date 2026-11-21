"""Inventory Book (periodic, D7): per item and warehouse, opening quantity,
quantity in, quantity out, closing quantity and the closing value at the last
valuation rate on the Stock Ledger."""

import frappe
from frappe import _
from frappe.utils import flt
from ph_cas.books.common import check_company


def execute(filters=None):
    f = frappe._dict(filters or {})
    check_company(f.get("company"))
    columns = [
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 180},
        {"fieldname": "item_name", "label": _("Description"), "fieldtype": "Data", "width": 200},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 160},
        {"fieldname": "uom", "label": _("Unit"), "fieldtype": "Data", "width": 70},
        {"fieldname": "opening_qty", "label": _("Opening qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "in_qty", "label": _("In"), "fieldtype": "Float", "width": 100},
        {"fieldname": "out_qty", "label": _("Out"), "fieldtype": "Float", "width": 100},
        {"fieldname": "count_qty", "label": _("Stock count adjustment"), "fieldtype": "Float", "width": 130},
        {"fieldname": "closing_qty", "label": _("Closing qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "valuation_rate", "label": _("Unit cost"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "closing_value", "label": _("Closing value"), "fieldtype": "Currency", "width": 130},
    ]
    # B82 (UAT LDG-221): quantities come from the stock ledger's running quantity, so a stock count
    # (Stock Reconciliation, which posts no in or out quantity) moves the closing figure; its effect
    # shows in its own column. The TOTAL row adds up every column.
    def last_qty(cond, args):
        return {(r.item_code, r.warehouse): flt(r.qty_after_transaction) for r in frappe.db.sql(
            f"""select sle.item_code, sle.warehouse, sle.qty_after_transaction from `tabStock Ledger Entry` sle
                join (select item_code, warehouse, max(posting_datetime) as at from `tabStock Ledger Entry`
                      where company = %(company)s and is_cancelled = 0 and {cond} group by item_code, warehouse) last
                  on last.item_code = sle.item_code and last.warehouse = sle.warehouse and last.at = sle.posting_datetime
                where sle.company = %(company)s and sle.is_cancelled = 0
                order by sle.creation""", args, as_dict=True)}

    args = {"company": f.company, "from_date": f.from_date, "to_date": f.to_date}
    opening = last_qty("posting_date < %(from_date)s", args)
    closing = last_qty("posting_date <= %(to_date)s", args)
    moves = frappe.db.sql(
        """select item_code, warehouse, sum(case when actual_qty > 0 then actual_qty else 0 end) as in_qty,
                  sum(case when actual_qty < 0 then -actual_qty else 0 end) as out_qty
           from `tabStock Ledger Entry` where company = %s and is_cancelled = 0 and posting_date between %s and %s
             and voucher_type != 'Stock Reconciliation'
           group by item_code, warehouse""",
        (f.company, f.from_date, f.to_date), as_dict=True)
    keys = set(opening) | set(closing) | {(m.item_code, m.warehouse) for m in moves}
    mv = {(m.item_code, m.warehouse): m for m in moves}
    rows = []
    tot = {"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "count_qty": 0.0, "closing_qty": 0.0, "closing_value": 0.0}
    for item, wh in sorted(keys):
        m = mv.get((item, wh))
        op = opening.get((item, wh), 0.0)
        inq = flt(m.in_qty) if m else 0.0
        outq = flt(m.out_qty) if m else 0.0
        close = closing.get((item, wh), flt(op + inq - outq))
        count = flt(close - (op + inq - outq), 6)
        last = frappe.db.sql(
            """select valuation_rate from `tabStock Ledger Entry` where company = %s and item_code = %s and warehouse = %s
               and is_cancelled = 0 and posting_date <= %s order by posting_date desc, posting_time desc, creation desc limit 1""",
            (f.company, item, wh, f.to_date))
        rate = flt(last[0][0]) if last else 0.0
        name, uom = frappe.db.get_value("Item", item, ["item_name", "stock_uom"]) or (item, "")
        value = flt(close * rate, 2)
        row = {"item_code": item, "item_name": name, "warehouse": wh, "uom": uom, "opening_qty": op, "in_qty": inq, "out_qty": outq, "count_qty": count, "closing_qty": close, "valuation_rate": rate, "closing_value": value}
        for k in tot:
            tot[k] += row[k]
        rows.append(row)
    rows.append({"item_code": _("TOTAL"), **{k: flt(v, 2) for k, v in tot.items()}, "is_total_row": 1})
    return columns, rows
