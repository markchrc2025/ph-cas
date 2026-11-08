"""B10: Philippine chart of accounts and account mapping."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.setup.chart import PURPOSES, account_for, setup_philippine_company
from ph_cas.tests.setup import TEST_ABBR, TEST_COMPANY


class TestB10Chart(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)

    def test_every_purpose_has_an_account_and_a_mapping(self):
        for purpose, spec in PURPOSES.items():
            acc = f"{spec['account']} - {TEST_ABBR}"
            self.assertTrue(frappe.db.exists("Account", acc), acc)
            self.assertEqual(account_for(TEST_COMPANY, purpose), acc)
            self.assertEqual(frappe.db.get_value("Account", acc, "root_type"), spec["root_type"])

    def test_setup_is_idempotent(self):
        out = setup_philippine_company(TEST_COMPANY)
        self.assertEqual(out["accounts"], [])
        self.assertEqual(out["mapping"], [])
        self.assertEqual(out["series"], [])

    def test_mapping_refuses_a_wrong_account(self):
        m = frappe.get_doc("PH Account Mapping", f"{TEST_COMPANY}-output_vat")
        m.account = f"Cash - {TEST_ABBR}"
        with self.assertRaises(frappe.ValidationError):
            m.save()
        m.reload()
        m.account = f"Duties and Taxes - {TEST_ABBR}"
        with self.assertRaises(frappe.ValidationError):
            m.save()

    def test_mapping_can_be_repointed_to_another_account_of_the_right_kind(self):
        acc = frappe.get_doc({"doctype": "Account", "account_name": "Output VAT Alt", "parent_account": f"Duties and Taxes - {TEST_ABBR}", "company": TEST_COMPANY, "account_type": "Tax"}).insert()
        m = frappe.get_doc("PH Account Mapping", f"{TEST_COMPANY}-output_vat")
        m.account = acc.name
        m.save()
        self.assertEqual(account_for(TEST_COMPANY, "output_vat"), acc.name)
        m.account = f"Output VAT - {TEST_ABBR}"
        m.save()

    def test_unknown_purpose_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({"doctype": "PH Account Mapping", "company": TEST_COMPANY, "purpose": "nope", "account": f"Cash - {TEST_ABBR}"}).insert()
