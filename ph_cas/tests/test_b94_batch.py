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
