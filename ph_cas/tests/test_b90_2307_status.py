"""B90: a 2307 prints clean, printing locks it, and it shows the bills behind the tax."""

import io

import frappe
from frappe.utils import add_days, flt, today
from pypdf import PdfReader

from ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued import generate_quarter, mark_issued, print_bir_form
from ph_cas.tests.fixtures import ensure_service_item, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY
from frappe.tests import IntegrationTestCase

from ph_cas.tests.test_b26_2307 import TestB26_2307


class TestB90_2307Status(IntegrationTestCase):
    setUp = TestB26_2307.setUp

    def _draft(self):
        pi = make_purchase_invoice(self.sup, [(ensure_service_item(), 1, 10000, {})], submit=True)
        generate_quarter(TEST_COMPANY, str(self.qs))
        return pi, frappe.get_doc("PH 2307 Issued", {"supplier": self.sup, "docstatus": 0})

    def test_sources_list_the_bills(self):
        pi, doc = self._draft()
        self.assertEqual([(s.source_doctype, s.source_name) for s in doc.sources], [("Purchase Invoice", pi.name)])
        self.assertEqual(flt(doc.sources[0].tax_withheld), flt(doc.total_tax))

    def test_print_locks_and_prints_clean(self):
        _pi, doc = self._draft()
        url = print_bir_form(doc.name)
        doc.reload()
        self.assertEqual(doc.docstatus, 1)
        self.assertEqual(doc.status, "Printed")
        self.assertEqual(doc.print_count, 1)
        self.assertTrue(doc.printed_on)
        self.assertNotIn("DRAFT", url)
        text = PdfReader(io.BytesIO(frappe.get_doc("File", {"file_url": url}).get_content())).pages[0].extract_text()
        self.assertNotIn("DRAFT", text)
        self.assertNotIn("NOT FILED", text)
        self.assertNotIn("Preview printed", text)
        print_bir_form(doc.name)
        doc.reload()
        self.assertEqual(doc.print_count, 2)
        self.assertEqual(doc.status, "Printed")

    def test_mark_issued_then_cancel_and_amend(self):
        _pi, doc = self._draft()
        with self.assertRaises(frappe.ValidationError):
            mark_issued(doc.name)  # not printed yet
        print_bir_form(doc.name)
        with self.assertRaises(frappe.ValidationError):
            mark_issued(doc.name, add_days(today(), 1))
        mark_issued(doc.name)
        doc.reload()
        self.assertEqual(doc.status, "Issued")
        self.assertEqual(str(doc.issued_on), today())
        doc.cancel()
        doc.reload()
        self.assertEqual(doc.status, "Cancelled")
        with self.assertRaises(frappe.ValidationError):
            print_bir_form(doc.name)
        amended = frappe.copy_doc(doc)
        amended.amended_from = doc.name
        amended.insert()
        self.assertEqual(amended.status, "Draft")
        self.assertTrue(amended.sources)
        print_bir_form(amended.name)
        amended.reload()
        self.assertEqual(amended.replaces, doc.name)
        self.assertEqual(amended.status, "Printed")
