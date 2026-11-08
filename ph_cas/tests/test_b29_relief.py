"""B29: summary lists of sales, purchases and importations."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from ph_cas.dat.relief import build_importations, build_purchases, build_sales, generate
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.fixtures import ensure_customer, ensure_service_item, ensure_supplier_profile, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _item, _set_regime


class TestB29Relief(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")
        frappe.db.set_value("Company", TEST_COMPANY, {"tax_id": "123-456-789", "ph_branch_code": "00000", "ph_rdo": "045", "ph_registered_name": "SAMPLE TAXPAYER CORP", "ph_business_style": "SAMPLE TRADING"}, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        self.qs, self.qe = quarter_bounds(today())

    def tearDown(self):
        _set_regime("Non-VAT")

    def test_sales_list_merges_per_tin(self):
        cust = ensure_customer("_Test PH SLSP Buyer")
        frappe.db.set_value("Customer", cust, {"ph_tin": "777-888-999", "ph_registered_name": "BUYER CORP", "ph_payee_type": "Non-individual", "ph_address_line1": "1 MAIN ST", "ph_address_line2": "PASIG"})
        frappe.clear_document_cache("Customer", cust)
        _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})], customer=cust, submit=True)
        _invoice([(_item("_PH Exempt", "VAT-exempt"), 1, 200, {})], customer=cust, submit=True)
        name, content, n = build_sales(TEST_COMPANY, self.qs, self.qe)
        lines = content.decode().split("\r\n")
        d = f"{self.qe.month:02d}/{self.qe.day:02d}/{self.qe.year}"
        self.assertTrue(lines[0].startswith(f'H,S,"123456789","SAMPLE TAXPAYER CORP","","","","SAMPLE TRADING","","",'))
        self.assertTrue(lines[0].endswith(f",045,{d},12"))
        rows = [l for l in lines if l.startswith("D,S,") and "777888999" in l]
        self.assertEqual(len(rows), 1)
        self.assertRegex(rows[0], rf'^D,S,"777888999","BUYER CORP","","","",1 MAIN ST,PASIG,(\d+\.\d\d),0\.00,(\d+\.\d\d),(\d+\.\d\d),123456789,{d}$')
        parts = rows[0].split(",")
        self.assertGreaterEqual(flt(parts[9]), 200)
        self.assertGreaterEqual(flt(parts[11]), 1000)
        self.assertEqual(name, f"123456789S{self.qe.month:02d}{self.qe.year}.DAT")

    def test_purchases_list(self):
        sup = ensure_supplier_profile("_Test PH VAT Supplier", ph_vat_status="VAT", ph_tin="888-999-000", ph_registered_name="SUPPLY CO", ph_ewt_category="None (no withholding)", ph_is_rbe=0, ph_is_nonresident_dsp=0)
        make_purchase_invoice(sup, [(ensure_service_item(), 1, 1000, {})], submit=True)
        name, content, n = build_purchases(TEST_COMPANY, self.qs, self.qe)
        lines = content.decode().split("\r\n")
        self.assertTrue(lines[0].startswith('H,P,"123456789","SAMPLE TAXPAYER CORP"'))
        self.assertEqual(len(lines[0].split(",")), 21)
        row = [l for l in lines if l.startswith("D,P,") and "888999000" in l][0]
        parts = row.split(",")
        self.assertEqual(parts[2], '"888999000"')
        self.assertGreaterEqual(flt(parts[11]), 1000)  # services
        self.assertGreaterEqual(flt(parts[14]), 120)  # input VAT
        self.assertEqual(name, f"123456789P{self.qe.month:02d}{self.qe.year}.DAT")

    def test_importations_list_and_2550q_item_46(self):
        from ph_cas.tax.returns import get_or_create

        imp = ensure_supplier_profile("_Test PH Foreign Supplier", ph_vat_status="Non-VAT", ph_ewt_category="None (no withholding)")
        d0 = get_or_create(TEST_COMPANY, "2550Q", self.qs, self.qe)
        f0 = {r.item: flt(r.amount) for r in d0.lines}
        pi = make_purchase_invoice(imp, [(ensure_service_item(), 1, 50000, {})], submit=True, ph_is_import=1, ph_import_entry_no="IE-2026-001", ph_import_assessment_date=today(), ph_import_date=today(), ph_import_country="CHINA", ph_import_dutiable_value=50000, ph_import_charges=5000, ph_input_vat_import=6600, ph_import_or_no="OR-77", ph_import_payment_date=today())
        self.assertEqual(flt(pi.ph_input_vat_import), 6600)
        self.assertTrue([t for t in pi.taxes if "importation" in t.description])
        name, content, n = build_importations(TEST_COMPANY, self.qs, self.qe)
        row = [l for l in content.decode().split("\r\n") if "IE-2026-001" in l][0]
        self.assertIn('"_TEST PH FOREIGN SUPPLIER"', row)
        self.assertIn("CHINA,50000.00,5000.00,", row)
        self.assertIn(",6600.00,OR-77,", row)
        self.assertEqual(name, f"123456789I{self.qe.month:02d}{self.qe.year}.DAT")
        d = get_or_create(TEST_COMPANY, "2550Q", self.qs, self.qe)
        f = {r.item: flt(r.amount) for r in d.lines}
        self.assertEqual(f["46A"] - f0["46A"], 50000)
        self.assertEqual(f["46B"] - f0["46B"], 6600)

    def test_generate_stores(self):
        name = generate(TEST_COMPANY, "S", str(self.qs), str(self.qe))
        self.assertEqual(frappe.db.get_value("PH Alphalist File", name, "layout_status"), "sample")
