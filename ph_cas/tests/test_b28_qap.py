"""B28: QAP 1601-EQ, 1604-E, MAP 1600-VT."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, getdate, get_first_day, get_last_day, today

from ph_cas.dat.qap import build_1600vt, build_1601eq, build_1604e, generate, unknown_atcs
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.fixtures import ensure_service_item, ensure_supplier_profile, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _set_regime


class TestB28QAP(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        frappe.db.set_value("Company", TEST_COMPANY, {"tax_id": "123-456-789", "ph_branch_code": "00000", "ph_rdo": "045", "ph_registered_name": "SAMPLE TAXPAYER CORP"}, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        self.qs, self.qe = quarter_bounds(today())
        self.ms, self.me = get_first_day(today()), get_last_day(today())
        self.lessor = ensure_supplier_profile("_Test PH QAP Lessor", ph_vat_status="Non-VAT", ph_payee_type="Individual", ph_last_name="Reyes", ph_first_name="Ana", ph_middle_name="B", ph_tin="222-333-444", ph_ewt_category="rent")
        make_purchase_invoice(self.lessor, [(ensure_service_item(), 1, 10000, {})], submit=True)
        self.corp = ensure_supplier_profile("_Test PH QAP Corp", ph_vat_status="Non-VAT", ph_payee_type="Non-individual", ph_registered_name="BUILDERS CORP", ph_tin="333-444-555", ph_ewt_category="contractor")
        make_purchase_invoice(self.corp, [(ensure_service_item(), 1, 5000, {})], submit=True, ph_no_withholding=1, ph_no_withholding_reason="Exempt payee per sworn declaration")

    def test_1601eq_schedules_1_and_2(self):
        name, content, n = build_1601eq(TEST_COMPANY, self.qs, self.qe)
        lines = content.decode().split("\r\n")
        p = f"{self.qe.month:02d}/{self.qe.year}"
        self.assertEqual(lines[0], f'HQAP,H1601EQ,123456789,00000,"SAMPLE TAXPAYER CORP",{p},045')
        d1 = [l for l in lines if l.startswith("D1,") and "222333444" in l][0]
        self.assertRegex(d1, rf'^D1,1601EQ,\d+,222333444,00000,"","REYES","ANA","B",{p},WI100,5\.00,\d+\.\d\d,\d+\.\d\d$')
        c1 = [l for l in lines if l.startswith("C1,")][0]
        self.assertTrue(c1.startswith(f"C1,1601EQ,123456789,00000,{p},"))
        d2 = [l for l in lines if l.startswith("D2,") and "333444555" in l][0]
        self.assertRegex(d2, rf'^D2,1601EQ,\d+,333444555,00000,"BUILDERS CORP","","","",{p},EI900,\d+\.\d\d$')
        c2 = [l for l in lines if l.startswith("C2,")][0]
        self.assertTrue(c2.startswith(f"C2,1601EQ,123456789,00000,{p},"))
        self.assertEqual(name, f"12345678900000{self.qe.month:02d}{self.qe.year}1601EQ.DAT")
        self.assertEqual(lines.index(c1) < lines.index(d2), True)

    def test_1604e(self):
        year = getdate(today()).year
        name, content, n = build_1604e(TEST_COMPANY, year)
        lines = content.decode().split("\r\n")
        self.assertEqual(lines[0], f"H1604E,123456789,00000,12/31/{year},N,0,045")
        d3 = [l for l in lines if l.startswith("D3,") and "222333444" in l][0]
        self.assertRegex(d3, rf'^D3,1604E,123456789,00000,12/31/{year},\d+,222333444,00000,"","REYES","ANA","B",WI100,\d+\.\d\d,5\.00,\d+\.\d\d$')
        self.assertTrue([l for l in lines if l.startswith("C3,1604E,123456789,00000,12/31/")])
        self.assertTrue([l for l in lines if l.startswith("D4,") and "333444555" in l])
        self.assertEqual(name, f"123456789000001231{year}1604E.DAT")

    def test_1600vt_map(self):
        _set_regime("VAT")
        try:
            dsp = ensure_supplier_profile("_Test PH Cloud Provider", ph_is_nonresident_dsp=1, ph_vat_status="Non-VAT", ph_tin=None, ph_registered_name="CLOUDCO LLC")
            make_purchase_invoice(dsp, [(ensure_service_item(), 1, 1000, {})], submit=True)
            name, content, n = build_1600vt(TEST_COMPANY, self.ms, self.me)
            lines = content.decode().split("\r\n")
            p = f"{self.me.month:02d}/{self.me.year}"
            self.assertEqual(lines[0], f'HMAP,H1600VT,123456789,00000,"SAMPLE TAXPAYER CORP",{p},045')
            dm = [l for l in lines if l.startswith("DMAP,")]
            self.assertTrue(dm, lines)
            d = [l for l in dm if "CLOUDCO" in l]
            self.assertTrue(d, dm)
            d = d[0]
            self.assertRegex(d, rf'^DMAP,D1600VT,\d+,000000000,00000,CLOUDCO LLC,,,,{p},WV080,,12\.00,\d+\.\d\d,\d+\.\d\d$')
            self.assertTrue([l for l in lines if l.startswith(f"CMAP,C1600VT,123456789,00000,{p},")])
            self.assertEqual(name, f"12345678900000{self.me.month:02d}{self.me.year}1600VT.DAT")
            self.assertNotIn("WV080", unknown_atcs())  # in the patched module 7.4 (July 2025)
        finally:
            _set_regime("Non-VAT")

    def test_generate_stores_with_status(self):
        name = generate(TEST_COMPANY, "1601EQ", str(self.qs), str(self.qe))
        doc = frappe.get_doc("PH Alphalist File", name)
        self.assertIn("verified-layout", doc.layout_status)
        self.assertTrue(doc.file_url)
