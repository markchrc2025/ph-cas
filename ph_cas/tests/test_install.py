import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.tests.setup import TEST_COMPANY


class TestInstall(IntegrationTestCase):
    def test_app_installed(self):
        self.assertIn("ph_cas", frappe.get_installed_apps())
        self.assertIn("erpnext", frappe.get_installed_apps())

    def test_setup_wizard_made_the_test_company(self):
        self.assertTrue(frappe.db.exists("Company", TEST_COMPANY))
        self.assertEqual(frappe.db.get_value("Company", TEST_COMPANY, "country"), "Philippines")
        self.assertEqual(frappe.db.get_value("Company", TEST_COMPANY, "default_currency"), "PHP")

    def test_company_can_be_created(self):
        name = "_Test PH Company B01"
        if not frappe.db.exists("Company", name):
            frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": name,
                    "abbr": "TPB",
                    "default_currency": "PHP",
                    "country": "Philippines",
                }
            ).insert()
        self.assertTrue(frappe.db.exists("Company", name))
