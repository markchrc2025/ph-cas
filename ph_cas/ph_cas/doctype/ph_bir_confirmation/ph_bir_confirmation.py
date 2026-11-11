"""PH BIR Confirmation: the BIR's Tax Return Receipt Confirmation e-mail as attached
to a return (or a System Manager's override). Read by ph_cas.forms.confirmation; the
file is kept so the filing basis can be shown later."""

import frappe
from frappe import _
from frappe.model.document import Document


class PHBIRConfirmation(Document):
    def validate(self):
        if self.kind == "Override" and not (self.reason or "").strip():
            frappe.throw(_("An override needs its reason."))
        if not self.attached_by:
            self.attached_by = frappe.session.user

    def on_trash(self):
        if self.tax_return and frappe.db.get_value("PH Tax Return", self.tax_return, "docstatus") == 1:
            frappe.throw(_("This confirmation is the filing basis of {0} and stays.").format(self.tax_return))
