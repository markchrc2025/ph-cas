"""B48: the owner's answers to the RDO questions (docs/DECISIONS.md, 14 Nov 2026)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, today

from ph_cas.books.yearend import build_pack
from ph_cas.dat.relief import months
from ph_cas.invoicing.rules import eis_required
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _item, _set_regime
from ph_cas.tests.test_b20_prints import render


def _company(**values):
    frappe.db.set_value("Company", TEST_COMPANY, values, update_modified=False)
    frappe.clear_document_cache("Company", TEST_COMPANY)


class TestB48RdoAnswers(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _company(ph_uses_eis=0, ph_ecommerce=0, ph_cr_atp_no="", ph_cr_atp_date=None)
        frappe.flags.ph_strict_manual_invoice_no = True

    def tearDown(self):
        frappe.flags.ph_strict_manual_invoice_no = False
        _company(ph_uses_eis=0, ph_ecommerce=0, ph_cr_atp_no="", ph_cr_atp_date=None, ph_taxpayer_class="Micro")

    # 2: the manual invoice number beside the system control number
    def test_manual_invoice_number_is_required_and_unique(self):
        si = make_sales_invoice(submit=False)
        with self.assertRaises(frappe.ValidationError):
            si.submit()
        si.reload()
        si.ph_manual_invoice_no = "MI-0001"
        si.submit()
        self.assertTrue(si.bir_serial)
        again = make_sales_invoice(submit=False)
        again.ph_manual_invoice_no = "MI-0001"
        with self.assertRaises(frappe.ValidationError):
            again.submit()

    def test_eis_company_needs_no_manual_number(self):
        _company(ph_uses_eis=1)
        si = make_sales_invoice(submit=False)
        si.submit()
        self.assertFalse(si.ph_manual_invoice_no)

    def test_invoice_prints_manual_number_and_system_control_number(self):
        _set_regime("VAT")
        try:
            si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})], submit=False)
            si.ph_manual_invoice_no = "MI-0420"
            si.submit()
            html = render(si, "PH Sales Invoice")
            self.assertIn("No. <b>MI-0420</b>", html)
            self.assertIn(f"System control no. {si.bir_serial}", html)
        finally:
            _set_regime("Non-VAT")

    # 1: e-invoicing for non-micro e-commerce taxpayers
    def test_eis_required_for_non_micro_ecommerce(self):
        _company(ph_ecommerce=1, ph_taxpayer_class="Micro")
        self.assertFalse(eis_required(TEST_COMPANY))
        _company(ph_ecommerce=1, ph_taxpayer_class="Small")
        self.assertTrue(eis_required(TEST_COMPANY))
        _company(ph_ecommerce=0, ph_taxpayer_class="Small")
        self.assertFalse(eis_required(TEST_COMPANY))

    # 9: the collection receipt prints its ATP, or the input-tax phrase without one
    def test_collection_receipt_atp_or_input_tax_phrase(self):
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        _set_regime("VAT")
        try:
            si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})], submit=False)
            si.ph_manual_invoice_no = "MI-0777"
            si.submit()
            pe = get_payment_entry("Sales Invoice", si.name)
            pe.reference_no = "CR-B48"
            pe.reference_date = today()
            pe.insert()
            pe.submit()
            self.assertIn("THIS DOCUMENT IS NOT VALID FOR CLAIM OF INPUT TAX", render(pe, "PH Collection Receipt"))
            _company(ph_cr_atp_no="ATP-2026-123", ph_cr_atp_date="2026-01-15")
            html = render(pe, "PH Collection Receipt")
            self.assertIn("ATP No. ATP-2026-123", html)
            self.assertNotIn("NOT VALID FOR CLAIM OF INPUT TAX", html)
        finally:
            _set_regime("Non-VAT")

    # 11: one SLSP file per month, three per quarter
    def test_quarter_is_three_months(self):
        m = months("2026-10-01", "2026-12-31")
        self.assertEqual([(str(a), str(b)) for a, b in m], [("2026-10-01", "2026-10-31"), ("2026-11-01", "2026-11-30"), ("2026-12-01", "2026-12-31")])

    # 5: the e-books pack carries the file layout description
    def test_ebooks_pack_has_file_layout(self):
        out = build_pack(TEST_COMPANY, getdate(today()).year)
        layout = out["files"]["FILE-LAYOUT.txt"].decode()
        self.assertIn("FILE LAYOUT DESCRIPTION", layout)
        self.assertIn("Decimals", layout)
        self.assertIn("FILE-LAYOUT.txt", out["manifest"]["files"])
        t = out["files"]["TRANSMITTAL.txt"].decode()
        self.assertIn("USB label:", t)
        self.assertIn("CSV (comma-separated text)", t)


class TestIncorporationDate(IntegrationTestCase):
    """Owner, 15 Nov 2026: a non-individual's date of incorporation is required once the TIN is set."""

    def test_required_for_non_individual_with_tin_only(self):
        frappe.set_user("Administrator")
        c = frappe.get_doc("Company", TEST_COMPANY)
        keep = (c.tax_id, c.get("ph_taxpayer_type"), c.get("ph_incorporation_date"))
        try:
            c.ph_taxpayer_type = "Non-individual"
            c.ph_incorporation_date = None
            c.tax_id = "123-456-789"
            with self.assertRaisesRegex(frappe.ValidationError, "incorporation"):
                c.save()
            c.reload()
            c.ph_taxpayer_type, c.ph_incorporation_date, c.tax_id = "Non-individual", None, ""
            c.save()  # no TIN yet (setup wizard): accepted
            c.reload()
            c.ph_taxpayer_type, c.ph_incorporation_date, c.tax_id = "Individual", None, "123-456-789"
            c.ph_last_name, c.ph_first_name = c.get("ph_last_name") or "Santos", c.get("ph_first_name") or "Maria"
            c.save()  # an individual has no incorporation date: accepted
            c.reload()
            c.ph_taxpayer_type, c.ph_incorporation_date, c.tax_id = "Non-individual", "2020-02-03", "123-456-789"
            c.save()
        finally:
            frappe.db.set_value("Company", TEST_COMPANY, {"tax_id": keep[0], "ph_taxpayer_type": keep[1], "ph_incorporation_date": keep[2]}, update_modified=False)
            frappe.clear_document_cache("Company", TEST_COMPANY)
