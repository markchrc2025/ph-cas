import frappe
from frappe import _
from frappe.model.document import Document


class PHApprovalChain(Document):
    def __setup__(self):
        # Blank company means every company. Frappe would otherwise fill a blank company
        # with the saving user's default company on insert, so a chain meant for every
        # company silently applied to one.
        self.dont_update_if_missing = ["company"]

    def on_update(self):
        # B82 (UAT LDG-205): an enabled chain on a site whose approval module was off was
        # silently ignored, so a 67,200.00 bill posted without approval. Enabling a chain now
        # switches the module on, and says so.
        from ph_cas.approvals.chains import module_on

        if self.enabled and not module_on():
            frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 1)
            frappe.msgprint(_("Approval chains were switched off for this business. Saving an enabled chain switched them on."), indicator="blue", alert=True)
