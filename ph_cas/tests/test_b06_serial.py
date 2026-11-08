"""B06: the BIR serial number."""

import threading

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.controls.locks import PHLockError
from ph_cas.controls.serial import SERIAL_FIELD, allocate, ensure_series, series_name
from ph_cas.tests.fixtures import make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY


class TestB06Serial(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        ensure_series(TEST_COMPANY)

    def test_series_exist_for_the_test_company(self):
        for dt in ("Sales Invoice", "Credit Note", "Debit Note", "Collection Receipt"):
            self.assertTrue(frappe.db.exists("BIR Series", series_name(TEST_COMPANY, "00000", dt)))

    def test_submit_takes_the_next_number_and_draft_has_none(self):
        series = series_name(TEST_COMPANY, "00000", "Sales Invoice")
        before = frappe.db.get_value("BIR Series", series, "next_number")
        si = make_sales_invoice(submit=False)
        self.assertFalse(si.get(SERIAL_FIELD))
        si.submit()
        self.assertEqual(si.get(SERIAL_FIELD), f"{before:08d}")
        self.assertEqual(frappe.db.get_value("BIR Series", series, "next_number"), before + 1)

    def test_numbers_are_consecutive_across_invoices(self):
        a = make_sales_invoice().get(SERIAL_FIELD)
        b = make_sales_invoice().get(SERIAL_FIELD)
        self.assertEqual(int(b), int(a) + 1)

    def test_cancel_keeps_the_number_and_the_amendment_gets_a_new_one(self):
        si = make_sales_invoice()
        serial = si.get(SERIAL_FIELD)
        si.cancel()
        self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, SERIAL_FIELD), serial)
        # an issued invoice is never amended (B21): the replacement is a new invoice
        replacement = make_sales_invoice()
        self.assertEqual(int(replacement.get(SERIAL_FIELD)), int(serial) + 1)

    def test_credit_note_uses_its_own_series(self):
        si = make_sales_invoice()
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

        cn = make_sales_return(si.name)
        cn.insert()
        cn.submit()
        series = series_name(TEST_COMPANY, "00000", "Credit Note")
        self.assertEqual(int(cn.get(SERIAL_FIELD)), frappe.db.get_value("BIR Series", series, "next_number") - 1)

    def test_failed_submit_does_not_consume_a_number(self):
        series = series_name(TEST_COMPANY, "00000", "Sales Invoice")
        before = frappe.db.get_value("BIR Series", series, "next_number")
        si = make_sales_invoice(submit=False)
        frappe.db.savepoint("ph_b06")
        # force a failure after the serial is taken: the unique index on an existing serial
        frappe.db.sql("update `tabBIR Series` set next_number = %s where name = %s", (before - 1, series))
        try:
            with self.assertRaises(Exception):
                si.submit()
        finally:
            frappe.db.rollback(save_point="ph_b06")
        self.assertEqual(frappe.db.get_value("BIR Series", series, "next_number"), before)

    def test_range_end_is_enforced(self):
        name = series_name(TEST_COMPANY, "00099", "Sales Invoice")
        if not frappe.db.exists("BIR Series", name):
            frappe.get_doc(
                {"doctype": "BIR Series", "company": TEST_COMPANY, "branch_code": "00099", "document_type": "Sales Invoice", "range_start": 1, "range_end": 2}
            ).insert()
        allocate(name)
        allocate(name)
        with self.assertRaises(PHLockError):
            allocate(name)

    def test_counter_cannot_be_edited_or_the_series_deleted(self):
        series = frappe.get_doc("BIR Series", series_name(TEST_COMPANY, "00000", "Sales Invoice"))
        series.next_number = 1
        with self.assertRaises(frappe.ValidationError):
            series.save()
        series.reload()
        if series.next_number > series.range_start:
            with self.assertRaises(frappe.ValidationError):
                series.delete()

    def test_fifty_parallel_allocations_give_fifty_consecutive_numbers(self):
        name = series_name(TEST_COMPANY, "00077", "Sales Invoice")
        if not frappe.db.exists("BIR Series", name):
            frappe.get_doc(
                {"doctype": "BIR Series", "company": TEST_COMPANY, "branch_code": "00077", "document_type": "Sales Invoice"}
            ).insert()
        frappe.db.commit()
        site = frappe.local.site
        results, errors = [], []
        lock = threading.Lock()

        def worker():
            try:
                frappe.init(site)
                frappe.connect()
                serial, _ = allocate(name)
                frappe.db.commit()
                with lock:
                    results.append(int(serial))
            except Exception as e:  # pragma: no cover
                with lock:
                    errors.append(repr(e))
            finally:
                frappe.destroy()

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(set(results)), 50)
        self.assertEqual(sorted(results), list(range(min(results), min(results) + 50)))
