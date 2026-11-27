"""B91: the Home checklist ticks from the company's work, per company."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.audit.events import record
from ph_cas.home import dashboard
from ph_cas.home.progress import MODULES_KEY, step_done
from ph_cas.tests.fixtures import make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY

OTHER = "_Test B91 Other Company"


class TestB91OnboardingProgress(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_company_setup(self):
        tin = frappe.db.get_value("Company", TEST_COMPANY, "tax_id")
        frappe.db.set_value("Company", TEST_COMPANY, "tax_id", "")
        self.assertFalse(step_done("PH Set Up Company", TEST_COMPANY))
        frappe.db.set_value("Company", TEST_COMPANY, "tax_id", tin or "000-123-456")
        self.assertTrue(step_done("PH Set Up Company", TEST_COMPANY))
        frappe.db.set_value("Company", TEST_COMPANY, "tax_id", tin)
        self.assertFalse(step_done("PH Set Up Company", OTHER))

    def test_invoice_printed_is_per_company(self):
        si = make_sales_invoice()
        frappe.flags.ph_print_record_writer = True
        try:
            frappe.get_doc({"doctype": "PH Print Record", "ref_doctype": "Sales Invoice", "ref_name": si.name, "print_no": 1, "copy_type": "original"}).insert(ignore_permissions=True)
        finally:
            frappe.flags.ph_print_record_writer = False
        self.assertTrue(step_done("PH First BIR Invoice", TEST_COMPANY))
        self.assertFalse(step_done("PH First BIR Invoice", OTHER))

    def test_books_and_pack_exports(self):
        record("export", "Report", "PH Sales Journal", 0, {"format": "Excel", "filters": {"company": TEST_COMPANY}})
        self.assertTrue(step_done("PH Export Books", TEST_COMPANY))
        self.assertFalse(step_done("PH Export Books", OTHER))
        record("export", "Company", TEST_COMPANY, 0, {"registration_pack": [], "gaps": []})
        self.assertTrue(step_done("PH Registration Pack", TEST_COMPANY))
        self.assertFalse(step_done("PH Registration Pack", OTHER))

    def test_modules_only_when_a_user_saves(self):
        frappe.db.set_default(MODULES_KEY, None)
        self.assertFalse(step_done("PH Choose Modules", TEST_COMPANY))
        frappe.get_single("PH Modules").save()
        self.assertTrue(step_done("PH Choose Modules", TEST_COMPANY))

    def test_tax_rules(self):
        drafts = frappe.get_all("PH Tax Rule", filters={"status": "draft"}, pluck="name")
        if not frappe.db.count("PH Tax Rule"):
            self.skipTest("no tax rules on the test site")
        self.assertEqual(step_done("PH Confirm Tax Rules", TEST_COMPANY), not drafts)
        # B96 (LDG-248): all confirmed ticks the step
        frappe.db.set_value("PH Tax Rule", {"status": "draft"}, "status", "confirmed") if drafts else None
        self.assertTrue(step_done("PH Confirm Tax Rules", TEST_COMPANY))
        for n in drafts:
            frappe.db.set_value("PH Tax Rule", n, "status", "draft")

    def test_return_computed(self):
        self.assertEqual(step_done("PH Run 2550Q", TEST_COMPANY), bool(frappe.db.exists("PH Tax Return", {"company": TEST_COMPANY, "docstatus": ["<", 2]})))
        self.assertFalse(step_done("PH Run 2550Q", OTHER))

    def test_home_uses_the_rules(self):
        frappe.defaults.clear_user_default("ph_home_hide_onboarding")
        ob = dashboard._onboarding(TEST_COMPANY)
        if ob is None:
            return  # every step done
        for s in ob["steps"]:
            expected = step_done(s["name"], TEST_COMPANY)
            if expected is not None:
                self.assertEqual(s["done"], expected, s["name"])
