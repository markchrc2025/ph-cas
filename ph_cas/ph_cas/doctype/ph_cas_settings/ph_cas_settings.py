import frappe
from frappe.model.document import Document


class PHCASSettings(Document):
    def validate(self):
        if (self.failed_signins_before_deactivation or 0) < 3:
            frappe.throw("Failed sign-ins before deactivation must be at least 3.")
        if not (self.product_name or "").strip():
            self.product_name = "PH CAS"
        if "erpnext" in self.product_name.lower():
            frappe.throw("The product name cannot contain the ERPNext trademark (decision D9).")
