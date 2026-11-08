import frappe
from frappe import _

from ph_cas.tax.rules import draft_rules


def execute(filters=None):
    columns = [
        {"fieldname": "rule_id", "label": _("Rule"), "fieldtype": "Link", "options": "PH Tax Rule", "width": 220},
        {"fieldname": "kind", "label": _("Kind"), "fieldtype": "Data", "width": 110},
        {"fieldname": "title", "label": _("Title"), "fieldtype": "Data", "width": 420},
        {"fieldname": "legal_basis", "label": _("Legal basis"), "fieldtype": "Data", "width": 320},
    ]
    return columns, draft_rules()
