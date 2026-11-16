"""B27: DAT framework and SAWT."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import get_first_day, get_last_day, today

from ph_cas.dat.sawt import build, generate
from ph_cas.dat.writer import file_name, fmt, record
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.fixtures import ensure_customer
from ph_cas.tests.setup import TEST_COMPANY


class TestB27SAWT(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        frappe.db.set_value("Company", TEST_COMPANY, {"tax_id": "123-456-789", "ph_branch_code": "00000", "ph_rdo": "045", "ph_registered_name": "SAMPLE TAXPAYER CORP"}, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        self.qs, self.qe = quarter_bounds(today())
        self.cust = ensure_customer("_Test PH SAWT Payor")
        frappe.db.set_value("Customer", self.cust, {"ph_tin": "111-222-333", "ph_branch_code": "00000", "ph_registered_name": "ACME PAYOR INC", "ph_payee_type": "Non-individual"})
        frappe.clear_document_cache("Customer", self.cust)
        for d in frappe.get_all("PH 2307 Received", filters={"customer": self.cust, "docstatus": 1}, pluck="name"):
            frappe.get_doc("PH 2307 Received", d).cancel()
        rec = frappe.get_doc({"doctype": "PH 2307 Received", "company": TEST_COMPANY, "customer": self.cust, "period_from": get_first_day(today()), "period_to": get_last_day(today()), "lines": [{"atc": "WC160", "kind": "Income tax", "month_1": 10000, "tax_withheld": 200}]}).insert()
        rec.submit()

    def test_formatting_primitives(self):
        self.assertEqual(fmt(1234.5, "n"), "1234.50")
        self.assertEqual(fmt("ACME, INC.", "q"), '"ACME, INC."')
        self.assertEqual(fmt("", "qe"), '""')
        self.assertEqual(fmt("2026-09-30", "p"), "09/2026")
        self.assertEqual(fmt("2026-12-31", "d"), "12/31/2026")
        self.assertEqual(record(["D1", 7, 100], ["u", "i", "n"]), "D1,7,100.00")
        self.assertEqual(file_name("123-456-789", "00000", "2026-09-30", "1601EQ"), "12345678900000920261601EQ.DAT")
        self.assertEqual(file_name("123-456-789", "00000", "2026-12-31", "1604E", kind="annual"), "1234567890000123120261604E.DAT")

    def test_sawt_1702q_layout(self):
        name, content, n = build(TEST_COMPANY, "1702Q", self.qs, self.qe)
        text = content.decode("ascii")
        lines = text.split("\r\n")
        self.assertEqual(lines[-1], "")  # trailing CRLF
        mmyyyy = f"{self.qe.month:02d}/{self.qe.year}"
        self.assertEqual(lines[0], f'HSAWT,H1702Q,123456789,0000,"SAMPLE TAXPAYER CORP","","","",{mmyyyy},045')
        d = [l for l in lines if l.startswith("DSAWT")]
        self.assertEqual(len(d), n)
        row = [l for l in d if "111222333" in l][0]
        self.assertEqual(row, f'DSAWT,D1702Q,{d.index(row) + 1},111222333,0000,"ACME PAYOR INC",,,,{mmyyyy},,WC160,2.00,10000.00,200.00')
        c = [l for l in lines if l.startswith("CSAWT")][0]
        self.assertTrue(c.startswith(f"CSAWT,C1702Q,123456789,0000,{mmyyyy},"))
        self.assertEqual(name, f"1234567890000{self.qe.month:02d}{self.qe.year}1702Q.DAT")
        self.assertNotIn("\n", text.replace("\r\n", ""))

    def test_individual_payor_uses_name_parts(self):
        ind = ensure_customer("_Test PH SAWT Individual")
        frappe.db.set_value("Customer", ind, {"ph_tin": "444-555-666", "ph_payee_type": "Individual", "ph_last_name": "Dela Cruz", "ph_first_name": "Juan", "ph_middle_name": "Santos", "ph_registered_name": None})
        frappe.clear_document_cache("Customer", ind)
        rec = frappe.get_doc({"doctype": "PH 2307 Received", "company": TEST_COMPANY, "customer": ind, "period_from": get_first_day(today()), "period_to": get_last_day(today()), "lines": [{"atc": "WI160", "kind": "Income tax", "month_1": 5000, "tax_withheld": 100}]}).insert()
        rec.submit()
        name, content, n = build(TEST_COMPANY, "1702Q", self.qs, self.qe)
        row = [l for l in content.decode().split("\r\n") if "444555666" in l][0]
        self.assertIn(',444555666,0000,,"DELA CRUZ","JUAN","SANTOS",', row)

    def test_generate_stores_file_with_hash(self):
        name = generate(TEST_COMPANY, "1702Q", str(self.qs), str(self.qe))
        doc = frappe.get_doc("PH Alphalist File", name)
        self.assertEqual(doc.layout_status, "verified")
        self.assertEqual(len(doc.sha256), 64)
        self.assertTrue(doc.file_url)
        doc.sha256 = "0" * 64
        with self.assertRaises(frappe.ValidationError):
            doc.save()

    def test_rows_sorted_by_tin(self):
        name, content, n = build(TEST_COMPANY, "1702Q", self.qs, self.qe)
        tins = [l.split(",")[3] for l in content.decode().split("\r\n") if l.startswith("DSAWT")]
        self.assertEqual(tins, sorted(tins))
