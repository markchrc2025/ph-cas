"""B21: invoicing rules."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from ph_cas.controls.locks import PHLockError
from ph_cas.invoicing.rules import make_end_of_day_invoice
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import ensure_customer, ensure_service_item
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _item, _set_regime


class TestB21InvoicingRules(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")

    def tearDown(self):
        _set_regime("Non-VAT")
        frappe.db.set_value("Company", TEST_COMPANY, "ph_use_collection_receipt", 1, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)

    def test_vat_buyer_over_1000_needs_tin_and_address(self):
        buyer = ensure_customer("_Test PH VAT Buyer No TIN")
        frappe.db.set_value("Customer", buyer, {"ph_vat_status": "VAT", "ph_tin": None, "tax_id": None, "ph_address_line1": None})
        frappe.clear_document_cache("Customer", buyer)
        with self.assertRaises(PHLockError):
            _invoice([(ensure_service_item(), 1, 1000, {})], customer=buyer)
        si = _invoice([(ensure_service_item(), 1, 800, {})], customer=buyer)  # 896 with VAT, below 1,000
        self.assertTrue(si.name)
        frappe.db.set_value("Customer", buyer, {"ph_tin": "333-444-555", "ph_address_line1": "12 Rizal St, Marikina"})
        frappe.clear_document_cache("Customer", buyer)
        si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=buyer)
        self.assertTrue(si.name)

    def test_non_vat_buyer_is_not_required_to_give_details(self):
        buyer = ensure_customer("_Test PH NonVAT Buyer")
        frappe.db.set_value("Customer", buyer, {"ph_vat_status": "Non-VAT", "ph_tin": None, "tax_id": None, "ph_address_line1": None})
        frappe.clear_document_cache("Customer", buyer)
        si = _invoice([(ensure_service_item(), 1, 5000, {})], customer=buyer)
        self.assertTrue(si.name)

    def test_issued_invoice_cannot_be_amended(self):
        si = _invoice([(ensure_service_item(), 1, 1000, {})], submit=True)
        si.cancel()
        amended = frappe.copy_doc(si)
        amended.amended_from = si.name
        amended.docstatus = 0
        with self.assertRaises(PHLockError):
            amended.insert()

    def test_credit_note_still_works_as_the_correction_path(self):
        si = _invoice([(ensure_service_item(), 1, 1000, {})], submit=True)
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

        cn = make_sales_return(si.name)
        cn.insert()
        cn.submit()
        self.assertEqual(cn.return_against, si.name)
        self.assertTrue(cn.bir_serial)

    def test_end_of_day_invoice(self):
        _set_regime("Non-VAT")
        walkin = ensure_customer("Walk-in Customers")
        frappe.db.set_value("Company", TEST_COMPANY, "ph_walkin_customer", walkin, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        name = make_end_of_day_invoice(TEST_COMPANY, today(), vatable=1850.50, exempt=120)
        si = frappe.get_doc("Sales Invoice", name)
        self.assertEqual(si.ph_end_of_day, 1)
        self.assertEqual(flt(si.ph_pt_base), 1850.50)
        self.assertEqual(flt(si.ph_exempt_sales), 120)
        self.assertEqual(si.customer, walkin)
        with self.assertRaises(frappe.ValidationError):
            make_end_of_day_invoice(TEST_COMPANY, "2026-01-01", vatable=100)

    def test_collection_receipt_switch(self):
        frappe.db.set_value("Company", TEST_COMPANY, "ph_use_collection_receipt", 0, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        si = _invoice([(ensure_service_item(), 1, 1000, {})], submit=True)
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        pe = get_payment_entry("Sales Invoice", si.name)
        pe.reference_no = "X"
        pe.reference_date = today()
        pe.insert()
        pe.submit()
        self.assertFalse(pe.bir_serial)
        with self.assertRaises(frappe.ValidationError):
            pe.run_method("before_print", frappe._dict({"method": "print"}))
