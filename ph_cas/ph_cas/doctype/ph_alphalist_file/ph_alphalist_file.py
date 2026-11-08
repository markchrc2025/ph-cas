import frappe
from frappe import _
from frappe.model.document import Document


class PHAlphalistFile(Document):
    def validate(self):
        before = self.get_doc_before_save()
        if before and (before.sha256 != self.sha256 or before.file_name != self.file_name) and not frappe.flags.get("ph_dat_writer"):
            frappe.throw(_("A generated file is never edited; generate a new one."))
