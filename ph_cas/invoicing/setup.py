import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def setup():
    """The PH print formats become the default print formats of their DocTypes.

    The 2307 has none: it prints only on the BIR's own blank (Print on BIR form,
    ph_cas.forms.f2307). The HTML look-alike PH BIR 2307 of B26 is disabled and
    stops being the default where an earlier version made it so."""
    frappe.db.delete("Property Setter", {"doc_type": "PH 2307 Issued", "property": "default_print_format", "value": "PH BIR 2307"})
    if frappe.db.exists("Print Format", "PH BIR 2307"):
        frappe.db.set_value("Print Format", "PH BIR 2307", "disabled", 1, update_modified=False)
    for doctype, fmt in (("Sales Invoice", "PH Sales Invoice"), ("Payment Entry", "PH Collection Receipt")):
        if not frappe.db.exists("Print Format", fmt):
            continue
        existing = frappe.db.get_value("Property Setter", {"doc_type": doctype, "property": "default_print_format"}, "value")
        if existing != fmt:
            make_property_setter(doctype, None, "default_print_format", fmt, "Data", for_doctype=True)
    frappe.clear_cache()
