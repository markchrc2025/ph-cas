"""B93: the client's failed sign-in threshold moves to PH Security Settings."""

import frappe


def execute():
    frappe.reload_doc("ph_cas", "doctype", "ph_security_settings")
    n = frappe.db.get_single_value("PH CAS Settings", "failed_signins_before_deactivation") or 5
    frappe.db.set_single_value("PH Security Settings", "failed_signins_before_deactivation", max(int(n), 3))
