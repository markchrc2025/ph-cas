"""B93: the client's own security choices (the provider's settings are in PH CAS Settings)."""

import frappe
from frappe import _
from frappe.model.document import Document


class PHSecuritySettings(Document):
    def validate(self):
        if (self.failed_signins_before_deactivation or 0) < 3:
            frappe.throw(_("Allow at least 3 failed sign-ins before a user is deactivated."))
