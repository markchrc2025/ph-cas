"""B02: nothing posted can be deleted or reposted."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.controls.locks import (
    FORCED_ACCOUNTS_SETTINGS,
    PHLockError,
    force_accounts_settings,
)
from ph_cas.tests.fixtures import make_journal_entry, make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY


class TestB02Locks(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    # (a) posted documents cannot be deleted, by anyone

    def test_submitted_journal_entry_cannot_be_deleted(self):
        je = make_journal_entry()
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("Journal Entry", je.name, force=True)
        self.assertTrue(frappe.db.exists("Journal Entry", je.name))

    def test_cancelled_journal_entry_cannot_be_deleted(self):
        je = make_journal_entry()
        je.cancel()
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("Journal Entry", je.name, force=True)
        self.assertTrue(frappe.db.exists("Journal Entry", je.name))

    def test_submitted_sales_invoice_cannot_be_deleted(self):
        si = make_sales_invoice()
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("Sales Invoice", si.name, force=True)

    def test_cancelled_sales_invoice_cannot_be_deleted_even_with_setting_toggled(self):
        """If the forced settings were ever flipped behind the validate hook, ph_cas
        still refuses the deletion. ERPNext's own on_trash removes the GL rows by
        raw SQL before doc_events run, so in a real request the refusal aborts the
        transaction and the rows come back with the rollback; here we roll back
        to a savepoint to check the same thing."""
        si = make_sales_invoice()
        si.cancel()
        frappe.db.savepoint("ph_b02_toggle")
        frappe.db.set_single_value("Accounts Settings", "delete_linked_ledger_entries", 1)
        frappe.db.set_single_value("Accounts Settings", "enable_immutable_ledger", 0)
        frappe.clear_cache(doctype="Accounts Settings")
        try:
            with self.assertRaises(PHLockError):
                frappe.delete_doc("Sales Invoice", si.name, force=True)
        finally:
            frappe.db.rollback(save_point="ph_b02_toggle")
            frappe.clear_cache(doctype="Accounts Settings")
        self.assertTrue(frappe.db.exists("Sales Invoice", si.name))
        self.assertTrue(frappe.db.exists("GL Entry", {"voucher_no": si.name}))

    def test_draft_can_still_be_deleted(self):
        je = make_journal_entry(submit=False)
        frappe.delete_doc("Journal Entry", je.name)
        self.assertFalse(frappe.db.exists("Journal Entry", je.name))

    def test_ledger_rows_cannot_be_deleted_directly(self):
        je = make_journal_entry()
        gle = frappe.db.get_value("GL Entry", {"voucher_no": je.name}, "name")
        self.assertTrue(gle)
        with self.assertRaises(PHLockError):
            frappe.delete_doc("GL Entry", gle, force=True)

    # (b) Delete Transactions, (c) reposts

    def test_transaction_deletion_record_cannot_be_created(self):
        with self.assertRaises(PHLockError):
            frappe.get_doc({"doctype": "Transaction Deletion Record", "company": TEST_COMPANY}).insert()

    def test_company_delete_transactions_entry_point_is_refused(self):
        from erpnext.setup.doctype.company.company import create_transaction_deletion_request

        with self.assertRaises(PHLockError):
            create_transaction_deletion_request(TEST_COMPANY)

    def test_repost_accounting_ledger_cannot_be_created(self):
        je = make_journal_entry()
        with self.assertRaises(PHLockError):
            frappe.get_doc(
                {
                    "doctype": "Repost Accounting Ledger",
                    "company": TEST_COMPANY,
                    "vouchers": [{"voucher_type": "Journal Entry", "voucher_no": je.name}],
                }
            ).insert()

    def test_repost_item_valuation_cannot_be_created(self):
        with self.assertRaises(PHLockError):
            frappe.get_doc(
                {
                    "doctype": "Repost Item Valuation",
                    "based_on": "Item and Warehouse",
                    "company": TEST_COMPANY,
                }
            ).insert()

    # (e) settings forced

    def test_accounts_settings_are_forced_and_cannot_be_turned_back(self):
        for field, value in FORCED_ACCOUNTS_SETTINGS.items():
            self.assertEqual(int(frappe.db.get_single_value("Accounts Settings", field)), value)
        settings = frappe.get_doc("Accounts Settings")
        settings.enable_immutable_ledger = 0
        with self.assertRaises(PHLockError):
            settings.save()
        settings.reload()
        settings.delete_linked_ledger_entries = 1
        with self.assertRaises(PHLockError):
            settings.save()

    def test_force_accounts_settings_is_idempotent(self):
        before = frappe.db.get_single_value("Accounts Settings", "modified")
        force_accounts_settings()
        force_accounts_settings()
        self.assertEqual(frappe.db.get_single_value("Accounts Settings", "modified"), before)

    # the escape hatch is ignored on a production site

    def test_unlock_flag_is_ignored_on_production(self):
        from ph_cas.controls import locks

        frappe.conf.ph_cas_production = 1
        frappe.conf.ph_cas_unlocked = 1
        try:
            self.assertTrue(locks.locks_active())
        finally:
            frappe.conf.pop("ph_cas_production", None)
            frappe.conf.pop("ph_cas_unlocked", None)
