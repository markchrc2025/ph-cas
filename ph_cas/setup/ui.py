"""B82: screen fixes from the UAT run (Sentire UAT Standard v1.0, build 0.1.0+1d56e40d2b40).

Idempotent; runs at every migrate (setup.install.setup_all).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

PROPERTIES = [
    # (doctype, field, property, value, type, why)
    ("Journal Entry", "user_remark", "hidden", 0, "Check"),  # LDG-190, 210, 211: ERPNext v16 hides it; the books print it as the particulars
    ("Accounting Period", "exempted_role", "hidden", 1, "Check"),  # LDG-211: no role may be exempted, so the field is not offered
]

FIELDS = {
    # LDG-192: the stock count carries a remark like every other stock document
    "Stock Reconciliation": [{"fieldname": "ph_remarks", "fieldtype": "Small Text", "label": "Remarks", "insert_after": "posting_time"}],
}


def setup():
    for doctype, field, prop, value, ptype in PROPERTIES:
        if frappe.get_meta(doctype).has_field(field):
            make_property_setter(doctype, field, prop, value, ptype, validate_fields_for_doctype=False)
    create_custom_fields(FIELDS, ignore_validate=True)
