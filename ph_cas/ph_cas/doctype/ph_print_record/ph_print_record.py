import frappe
from frappe import _
from frappe.model.document import Document


class PHPrintRecord(Document):
    def validate(self):
        if not self.is_new() or not frappe.flags.get("ph_print_record_writer"):
            frappe.throw(_("Print records are written by the system only."), frappe.PermissionError)

    def on_trash(self):
        frappe.throw(_("Print records cannot be deleted."), frappe.PermissionError)
