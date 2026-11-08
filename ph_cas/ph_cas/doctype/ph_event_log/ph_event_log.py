import frappe
from frappe import _
from frappe.model.document import Document


class PHEventLog(Document):
    """Append-only. Rows are written only through ph_cas.audit.events.record."""

    def validate(self):
        if not self.is_new():
            frappe.throw(_("Event log rows cannot be changed."), frappe.PermissionError)
        if not frappe.flags.get("ph_event_log_writer"):
            frappe.throw(_("Event log rows are written by the system only."), frappe.PermissionError)

    def on_trash(self):
        frappe.throw(_("Event log rows cannot be deleted."), frappe.PermissionError)
