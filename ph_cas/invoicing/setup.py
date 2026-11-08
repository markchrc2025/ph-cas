import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def setup():
    """The PH print formats become the default print formats of their DocTypes."""
    for doctype, fmt in (("Sales Invoice", "PH Sales Invoice"), ("Payment Entry", "PH Collection Receipt")):
        if not frappe.db.exists("Print Format", fmt):
            continue
        existing = frappe.db.get_value("Property Setter", {"doc_type": doctype, "property": "default_print_format"}, "value")
        if existing != fmt:
            make_property_setter(doctype, None, "default_print_format", fmt, "Data", for_doctype=True)
    frappe.clear_cache()
