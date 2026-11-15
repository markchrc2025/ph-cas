"""The owner, 15 Nov 2026: the role "PH Accounting Manager" is now "Accounting
Manager" (no "PH"). Renamed in place, so every user who holds it, and every
permission row that names it, follows."""

import frappe

OLD = "PH Accounting Manager"
NEW = "Accounting Manager"


def execute():
    if frappe.db.exists("Role", OLD) and not frappe.db.exists("Role", NEW):
        frappe.rename_doc("Role", OLD, NEW, force=True, show_alert=False)
        frappe.db.set_value("Role", NEW, "role_name", NEW, update_modified=False)
    elif frappe.db.exists("Role", OLD):
        # Both exist (the new one created first): move the holders, then drop the old one.
        frappe.db.sql("update `tabHas Role` set role=%s where role=%s", (NEW, OLD))
        frappe.db.sql("update `tabCustom DocPerm` set role=%s where role=%s", (NEW, OLD))
        frappe.db.sql("update `tabDocPerm` set role=%s where role=%s", (NEW, OLD))
        frappe.delete_doc("Role", OLD, force=True, ignore_permissions=True)
    frappe.clear_cache()
