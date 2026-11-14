"""B09: Philippine master data."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.setup.master_data import dat_branch, normalize_tin, payee_name_parts
from ph_cas.tests.setup import TEST_COMPANY


class TestB09MasterData(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_rdo_table_is_seeded(self):
        self.assertEqual(frappe.db.count("PH RDO"), 138)
        self.assertTrue(frappe.db.exists("PH RDO", "041"))
        self.assertTrue(frappe.db.exists("PH RDO", "53A"))

    def test_company_fields_exist_and_validate(self):
        c = frappe.get_doc("Company", TEST_COMPANY)
        for f in ("ph_registered_name", "ph_branch_code", "ph_rdo", "ph_vat_status", "ph_taxpayer_class", "ph_accn"):
            self.assertTrue(c.meta.has_field(f), f)
        c.tax_id = "123456789"
        c.ph_branch_code = "00000"
        c.ph_rdo = "041"
        c.ph_vat_status = "VAT"
        c.save()
        c.reload()
        self.assertEqual(c.tax_id, "123-456-789")
        self.assertEqual(c.ph_registered_name, TEST_COMPANY)
        c.ph_branch_code = "001"
        with self.assertRaises(frappe.ValidationError):
            c.save()

    def test_tin_with_branch_is_refused(self):
        c = frappe.get_doc("Company", TEST_COMPANY)
        c.tax_id = "123-456-789-00000"
        with self.assertRaises(frappe.ValidationError):
            c.save()

    def test_individual_payee_needs_a_split_name(self):
        s = frappe.get_doc({"doctype": "Supplier", "supplier_name": "Juan Dela Cruz", "supplier_group": "Services", "supplier_type": "Individual", "ph_payee_type": "Individual", "ph_tin": "111222333"})
        with self.assertRaises(frappe.ValidationError):
            s.insert()
        s.ph_last_name = "Dela Cruz"
        s.ph_first_name = "Juan"
        s.insert()
        self.assertEqual(s.ph_tin, "111-222-333")
        self.assertEqual(s.tax_id, "111-222-333")
        parts = payee_name_parts("Supplier", s.name)
        self.assertEqual(parts, {"registered_name": "", "last": "Dela Cruz", "first": "Juan", "middle": ""})

    def test_non_individual_payee_gets_registered_name(self):
        c = frappe.get_doc({"doctype": "Customer", "customer_name": "Acme Trading Corp", "customer_group": "Commercial", "territory": "All Territories", "tax_id": "222333444"})
        c.insert()
        self.assertEqual(c.ph_tin, "222-333-444")
        self.assertEqual(c.ph_registered_name, "Acme Trading Corp")
        self.assertEqual(c.ph_branch_code, "00000")
        self.assertEqual(payee_name_parts("Customer", c.name)["registered_name"], "Acme Trading Corp")

    def test_vat_class_fetches_from_item_to_line(self):
        from ph_cas.tests.fixtures import ensure_service_item, make_sales_invoice

        item = frappe.get_doc("Item", ensure_service_item())
        item.ph_vat_class = "VAT-exempt"
        item.save()
        try:
            si = make_sales_invoice(submit=False)
            self.assertEqual(si.items[0].ph_vat_class, "VAT-exempt")
        finally:
            item.ph_vat_class = "VATable"
            item.save()

    def test_dat_branch_code(self):
        # RDO answer 8b: the full 5-digit code, leading zeroes kept
        self.assertEqual(dat_branch("00000"), "00000")
        self.assertEqual(dat_branch("00012"), "00012")
        self.assertEqual(dat_branch("10000"), "10000")
        with self.assertRaises(frappe.ValidationError):
            dat_branch("123")

    def test_normalize_tin(self):
        self.assertEqual(normalize_tin("123456789"), "123-456-789")
        self.assertEqual(normalize_tin("123-456-789"), "123-456-789")

    def test_serial_branch_comes_from_the_company(self):
        from ph_cas.controls.serial import ensure_series, series_name
        from ph_cas.tests.fixtures import make_sales_invoice

        frappe.db.set_value("Company", TEST_COMPANY, "ph_branch_code", "00001", update_modified=False)
        frappe.clear_cache(doctype="Company")
        ensure_series(TEST_COMPANY, "00001")
        try:
            si = make_sales_invoice()
            self.assertEqual(si.ph_branch_code, "00001")
            self.assertEqual(int(si.bir_serial), frappe.db.get_value("BIR Series", series_name(TEST_COMPANY, "00001", "Sales Invoice"), "next_number") - 1)
        finally:
            frappe.db.set_value("Company", TEST_COMPANY, "ph_branch_code", "00000", update_modified=False)
            frappe.clear_cache(doctype="Company")
