"""B62 (LDG-48): the QAP, 1604-E, MAP and SAWT writers reproduce the BIR Alphalist
Data Entry module 7.4's own files byte for byte, and the books feed them the way the
module expects (monthly QAP files, no file for a month without payees, 4-digit branch
codes, the ATC's rate)."""

import os

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.dat.qap import annual_file, build_1601eq, generate, map_file, qap_file
from ph_cas.dat.sawt import _code, sawt_file
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import (
    ensure_service_item,
    ensure_supplier_profile,
    make_purchase_invoice,
)
from ph_cas.tests.setup import TEST_COMPANY

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden", "alphalist")
AGENT = {"tin": "474079835", "branch": "0000", "name": "SAMPLE TAXPAYER CORP", "rdo": "047", "individual": False, "last": "", "first": "", "middle": ""}


def golden(name):
    with open(os.path.join(GOLDEN, name), "rb") as f:
        return f.read()


def company(tin, name, **row):
    return {"tin": tin, "branch": "0000", "registered_name": name, "last": "", "first": "", "middle": "", **row}


def person(tin, last, first, middle, **row):
    return {"tin": tin, "branch": "0000", "registered_name": "", "last": last, "first": first, "middle": middle, **row}


BAYANI, MABUHAY, GLOBAL = "BAYANI RETAIL STORES INC", "MABUHAY MULTIPURPOSE COOPERATIVE", "GLOBAL ADS PTE LTD"


class TestB62AlphalistGolden(IntegrationTestCase):
    def test_qap_september_matches_module(self):
        s1 = [
            company("123456789", BAYANI, atc="WC120", rate=2, income=20000.50, tax=400.01),
            company("123456789", BAYANI, atc="WC158", rate=1, income=100000, tax=1000),
            person("234567890", "DELA CRUZ", "JUAN", "SANTOS", atc="WI010", rate=5, income=50000, tax=2500),
        ]
        s2 = [company("345678901", MABUHAY, atc="IC010", income=30000)]
        self.assertEqual(qap_file(AGENT, "2026-09-30", s1, s2), golden("47407983500000920261601EQ.DAT"))

    def test_qap_month_without_exempt_payees_has_no_schedule_2(self):
        s1 = [company("123456789", BAYANI, atc="WC158", rate=1, income=50000, tax=500)]
        self.assertEqual(qap_file(AGENT, "2026-07-31", s1, []), golden("47407983500000720261601EQ.DAT"))

    def test_1604e_matches_module(self):
        s3 = [
            company("123456789", BAYANI, atc="WC120", rate=2, income=20000.50, tax=400.01),
            company("123456789", BAYANI, atc="WC158", rate=1, income=150000, tax=1500),
            person("234567890", "DELA CRUZ", "JUAN", "SANTOS", atc="WI010", rate=5, income=50000, tax=2500),
        ]
        s4 = [company("345678901", MABUHAY, atc="IC010", income=30000)]
        self.assertEqual(annual_file(AGENT, "2026-12-31", s3, s4), golden("4740798350000123120261604E.DAT"))

    def test_map_matches_module(self):
        rows = [
            company("000000000", GLOBAL, atc="WV070", rate=12, income=10000, tax=1200),
            company("123456789", BAYANI, atc="WV050", rate=12, income=5000, tax=600),
        ]
        # the module sorts by name: BAYANI before GLOBAL, whatever the TIN
        self.assertEqual(map_file(AGENT, "2026-10-31", rows), golden("47407983500001020261600VT.DAT"))

    def test_sawt_matches_module(self):
        rows = [
            company("123456789", BAYANI, atc="WV010", rate=5, income=100000, tax=5000),
            person("234567890", "DELA CRUZ", "JUAN", "SANTOS", atc="WV020", rate=5, income=40000, tax=2000),
        ]
        self.assertEqual(sawt_file(AGENT, "2550Q", "2026-09-30", rows), golden("47407983500000920262550Q.DAT"))

    def test_sawt_form_codes_the_module_lists(self):
        self.assertEqual(_code("1702-RT"), "1702")
        self.assertEqual(_code("1702Q"), "1702Q")
        self.assertEqual(_code("2550Q"), "2550Q")


class TestB62QAPFromTheBooks(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        frappe.db.set_value("Company", TEST_COMPANY, {"tax_id": "474-079-835", "ph_branch_code": "00000", "ph_rdo": "047", "ph_registered_name": "SAMPLE TAXPAYER CORP"}, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        self.payee = ensure_supplier_profile("_Test PH B62 Contractor", ph_vat_status="Non-VAT", ph_payee_type="Non-individual", ph_registered_name="B62 BUILDERS CORP", ph_tin="456-789-012", ph_branch_code="00000", ph_ewt_category="contractor")
        # the third quarter of 2026, with payments in its first and third months only
        for d in frappe.get_all("Purchase Invoice", filters={"supplier": self.payee, "docstatus": 1}, pluck="name"):
            frappe.get_doc("Purchase Invoice", d).cancel()
        make_purchase_invoice(self.payee, [(ensure_service_item(), 1, 33.33, {})], submit=True, posting_date="2026-07-15", set_posting_time=1, ph_backdate_reason="Test: a past quarter")
        make_purchase_invoice(self.payee, [(ensure_service_item(), 1, 10000, {})], submit=True, posting_date="2026-09-10", set_posting_time=1, ph_backdate_reason="Test: a past quarter")

    def test_one_file_per_month_with_payees(self):
        files = build_1601eq(TEST_COMPANY, "2026-07-01", "2026-09-30")
        names = [f[0] for f in files]
        self.assertEqual(names, ["47407983500000720261601EQ.DAT", "47407983500000920261601EQ.DAT"])  # no August file
        july = files[0][1].decode().split("\r\n")
        self.assertEqual(july[0], 'HQAP,H1601EQ,474079835,0000,"SAMPLE TAXPAYER CORP",07/2026,047')
        row = [l for l in july if "456789012" in l][0]
        # the ATC's rate, not tax over income (0.67 / 33.33 would print 2.01)
        self.assertRegex(row, r'^D1,1601EQ,1,456789012,0000,"B62 BUILDERS CORP",,,,07/2026,WC120,2\.00,33\.33,0\.67$')
        self.assertFalse([l for l in july if l.startswith(("D2,", "C2,"))])

    def test_generate_stores_each_month(self):
        names = generate(TEST_COMPANY, "1601EQ", "2026-07-01", "2026-09-30")
        self.assertEqual(len(names), 2)
        docs = [frappe.get_doc("PH Alphalist File", n) for n in names]
        self.assertEqual([str(d.period_end) for d in docs], ["2026-07-31", "2026-09-30"])
        self.assertEqual({d.layout_status for d in docs}, {"verified"})
        self.assertEqual(generate(TEST_COMPANY, "1601EQ", "2026-04-01", "2026-06-30"), [])

    def test_no_file_without_payees(self):
        # the validator rejects a file with no detail ("No Detail Record found in file!")
        self.assertIsNone(generate(TEST_COMPANY, "1600VT", "2026-04-01", "2026-04-30"))
        from ph_cas.dat.sawt import generate as sawt_generate

        with self.assertRaises(frappe.ValidationError):
            sawt_generate(TEST_COMPANY, "2551Q", "2026-04-01", "2026-06-30")


class TestB62Names(IntegrationTestCase):
    def test_names_the_validator_accepts(self):
        from ph_cas.dat.writer import clean_name

        # the validator refuses ' & , and Ñ ("Invalid character on field Registered Name")
        self.assertEqual(clean_name("Builders & Sons, Inc."), "BUILDERS AND SONS INC.")
        self.assertEqual(clean_name("Peña's Bakery"), "PENAS BAKERY")
        self.assertEqual(clean_name("A/B (PH) #1"), "A/B (PH) #1")
        self.assertEqual(clean_name(None), "")
