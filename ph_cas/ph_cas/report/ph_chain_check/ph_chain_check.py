"""PH Chain Check: verifies the event log's hash chain on demand."""

import frappe
from frappe import _

from ph_cas.audit.events import verify_chain


def execute(filters=None):
    result = verify_chain()
    total = frappe.db.count("PH Event Log")
    last = frappe.db.get_value("PH Event Log", {"seq": total}, ["timestamp", "hash"], as_dict=True) if total else None
    columns = [
        {"fieldname": "check", "label": _("Check"), "fieldtype": "Data", "width": 260},
        {"fieldname": "value", "label": _("Result"), "fieldtype": "Data", "width": 500},
    ]
    rows = [
        {"check": _("Chain intact"), "value": _("YES") if result["ok"] else _("NO: broken at sequence {0} ({1})").format(result["first_bad_seq"], result["reason"])},
        {"check": _("Rows checked"), "value": str(result["checked"])},
        {"check": _("Rows in the log"), "value": str(total)},
        {"check": _("Latest row"), "value": f"{last.timestamp} {last.hash}" if last else ""},
        {"check": _("Last scheduled check"), "value": str(frappe.db.get_single_value("PH CAS Settings", "last_chain_check") or _("never"))},
    ]
    return columns, rows
