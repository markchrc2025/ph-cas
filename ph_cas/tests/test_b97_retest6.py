"""B97: fixes from UAT retest 6 (28 Nov 2026)."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.tests.test_b96_retest5 import _staff


class TestB97Retest6(IntegrationTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")

    def test_staff_cannot_record_an_expense(self):  # LDG-183
        from ph_cas import expense

        frappe.set_user(_staff())
        with self.assertRaises(frappe.PermissionError):
            expense.record_expense(supplier="x", amount=100)
