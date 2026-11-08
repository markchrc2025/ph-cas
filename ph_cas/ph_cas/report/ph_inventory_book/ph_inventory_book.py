"""Inventory Book (periodic, D7): per item and warehouse, opening quantity,
quantity in, quantity out, closing quantity and the closing value at the last
valuation rate on the Stock Ledger."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    f = frappe._dict(filters or {})
    columns = [
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 180},
        {"fieldname": "item_name", "label": _("Description"), "fieldtype": "Data", "width": 200},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 160},
        {"fieldname": "uom", "label": _("Unit"), "fieldtype": "Data", "width": 70},
        {"fieldname": "opening_qty", "label": _("Opening qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "in_qty", "label": _("In"), "fieldtype": "Float", "width": 100},
        {"fieldname": "out_qty", "label": _("Out"), "fieldtype": "Float", "width": 100},
        {"fieldname": "closing_qty", "label": _("Closing qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "valuation_rate", "label": _("Unit cost"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "closing_value", "label": _("Closing value"), "fieldtype": "Currency", "width": 130},
    ]
    opening = {}
    for r in frappe.db.sql(
        """select item_code, warehouse, coalesce(sum(actual_qty), 0) as qty from `tabStock Ledger Entry`
           where company = %s and is_cancelled = 0 and posting_date < %s group by item_code, warehouse""",
        (f.company, f.from_date), as_dict=True):
        opening[(r.item_code, r.warehouse)] = flt(r.qty)
    moves = frappe.db.sql(
        """select item_code, warehouse, sum(case when actual_qty > 0 then actual_qty else 0 end) as in_qty,
                  sum(case when actual_qty < 0 then -actual_qty else 0 end) as out_qty
           from `tabStock Ledger Entry` where company = %s and is_cancelled = 0 and posting_date between %s and %s
           group by item_code, warehouse""",
        (f.company, f.from_date, f.to_date), as_dict=True)
    keys = set(opening) | {(m.item_code, m.warehouse) for m in moves}
    mv = {(m.item_code, m.warehouse): m for m in moves}
    rows, total_value = [], 0.0
    for item, wh in sorted(keys):
        m = mv.get((item, wh))
        op = opening.get((item, wh), 0.0)
        inq = flt(m.in_qty) if m else 0.0
        outq = flt(m.out_qty) if m else 0.0
        close = flt(op + inq - outq)
        last = frappe.db.sql(
            """select valuation_rate from `tabStock Ledger Entry` where company = %s and item_code = %s and warehouse = %s
               and is_cancelled = 0 and posting_date <= %s order by posting_date desc, posting_time desc, creation desc limit 1""",
            (f.company, item, wh, f.to_date))
        rate = flt(last[0][0]) if last else 0.0
        name, uom = frappe.db.get_value("Item", item, ["item_name", "stock_uom"]) or (item, "")
        value = flt(close * rate, 2)
        total_value += value
        rows.append({"item_code": item, "item_name": name, "warehouse": wh, "uom": uom, "opening_qty": op, "in_qty": inq, "out_qty": outq, "closing_qty": close, "valuation_rate": rate, "closing_value": value})
    rows.append({"item_code": _("TOTAL"), "closing_value": flt(total_value, 2), "is_total_row": 1})
    return columns, rows
