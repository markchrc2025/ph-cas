import frappe
from frappe import _
from frappe.model.document import Document


class BIRSeries(Document):
    def validate(self):
        self.branch_code = (self.branch_code or "00000").strip()
        if not (self.branch_code.isdigit() and len(self.branch_code) == 5):
            frappe.throw(_("Branch code must be exactly 5 digits."))
        self.digits = 8
        if self.range_start < 1 or self.range_end < self.range_start:
            frappe.throw(_("The registered range must start at 1 or more and end at or after its start."))
        if self.range_end > 10**self.digits - 1:
            frappe.throw(_("The range end does not fit in {0} digits.").format(self.digits))
        if self.is_new():
            self.next_number = self.range_start
        else:
            before = self.get_doc_before_save()
            if before and before.next_number != self.next_number:
                frappe.throw(_("The next number is set by the system and cannot be edited."))
            if before and before.next_number > self.range_start and self.range_start != before.range_start:
                frappe.throw(_("The range start cannot change once numbers have been issued."))

    def on_trash(self):
        if self.next_number > self.range_start:
            frappe.throw(_("A BIR Series that has issued numbers cannot be deleted."))
