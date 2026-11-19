"""PH Cash Position (B74): cash and bank, the day's beginning balance, receipts, payments and
ending balance per account (ph_cas.books.cash)."""

from frappe import _

from ph_cas.books.cash import cash_position


def execute(filters=None):
    f = filters or {}
    columns = [
        {"fieldname": "account", "label": _("Cash or bank account"), "fieldtype": "Link", "options": "Account", "width": 260},
        {"fieldname": "account_type", "label": _("Type"), "fieldtype": "Data", "width": 80},
        {"fieldname": "opening", "label": _("Beginning balance"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "received", "label": _("Received"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "paid", "label": _("Paid out"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "closing", "label": _("Ending balance"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "entries", "label": _("Entries"), "fieldtype": "Int", "width": 80},
    ]
    p = cash_position(f.get("company"), f.get("day"))
    rows = list(p["accounts"])
    rows.append({"account": _("Total"), "account_type": "", **p["total"], "entries": sum(r["entries"] for r in p["accounts"]), "bold": 1})
    chart = {"data": {"labels": [r["account"].rsplit(" - ", 1)[0] for r in p["accounts"]],
                      "datasets": [{"name": _("Ending balance"), "values": [r["closing"] for r in p["accounts"]]}]}, "type": "bar"}
    return columns, rows, None, chart
