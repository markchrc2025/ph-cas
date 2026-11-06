import frappe
from frappe.tests import IntegrationTestCase


class TestInstall(IntegrationTestCase):
    def test_app_installed(self):
        self.assertIn("ph_cas", frappe.get_installed_apps())
        self.assertIn("erpnext", frappe.get_installed_apps())

    def test_company_can_be_created(self):
        name = "_Test PH Company B01"
        if frappe.db.exists("Company", name):
            frappe.delete_doc("Company", name, force=True)
        company = frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": name,
                "abbr": "TPB",
                "default_currency": "PHP",
                "country": "Philippines",
            }
        ).insert()
        self.assertTrue(frappe.db.exists("Company", company.name))
