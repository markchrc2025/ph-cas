"""B90: status for existing 2307s, and the bills and payments behind each one."""

import frappe


def execute():
    frappe.reload_doc("ph_cas", "doctype", "ph_2307_issued_source")
    frappe.reload_doc("ph_cas", "doctype", "ph_2307_issued")
    for c in frappe.get_all("PH 2307 Issued", fields=["name", "docstatus", "issued_on"]):
        status = {0: "Draft", 2: "Cancelled"}.get(c.docstatus) or ("Issued" if c.issued_on else "Printed")
        frappe.db.set_value("PH 2307 Issued", c.name, "status", status, update_modified=False)
        doc = frappe.get_doc("PH 2307 Issued", c.name)
        if doc.get("sources"):
            continue
        doc.generate()
        for row in doc.sources:
            row.db_insert()
