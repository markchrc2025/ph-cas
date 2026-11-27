"""B94: fixes from the owner's human tests of 25 to 27 Nov 2026."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.controls import delete_guard
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import make_journal_entry
from ph_cas.tests.setup import TEST_COMPANY


class TestB94Batch(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)

    def test_form_delete_of_a_cancelled_journal_gives_the_posted_message(self):  # JP-003
        je = make_journal_entry(amount=77)
        je.cancel()
        with self.assertRaises(frappe.ValidationError) as e:
            delete_guard.get_linked_docs_to_delete("Journal Entry", je.name)
        self.assertIn("has been posted and cannot be deleted", str(e.exception))
        self.assertIn("ph_cas.controls.delete_guard.get_linked_docs_to_delete", frappe.get_hooks("override_whitelisted_methods").get("frappe.desk.form.linked_with.get_linked_docs_to_delete", []))

    def test_staff_reads_bills_journals_suppliers_and_returns_but_changes_none(self):  # BR-005 note
        from ph_cas.setup import roles as R

        email = "b94.staff@example.test"
        if not frappe.db.exists("User", email):
            u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "B94", "send_welcome_email": 0, "ph_provider_staff": 1})
            u.flags.ignore_permissions = True
            u.insert()
            u.add_roles(R.CASHIER_ROLE, "Accounts User", "Sales User")
        for dt in ("Purchase Invoice", "Journal Entry", "Supplier", "PH Tax Return", "PH 2307 Issued"):
            self.assertTrue(R.cashier_limit(dt, "read", email), dt)
            self.assertFalse(R.cashier_limit(dt, "create", email), dt)
            self.assertFalse(R.cashier_limit(dt, "write", email), dt)
            self.assertEqual(R.counter_query(email, dt), "")
        self.assertFalse(R.cashier_limit(frappe._dict(doctype="Payment Entry", payment_type="Pay"), "create", email))
        self.assertIn("PH Approval Chain", R.COUNTER_HIDDEN)
