"""G3: the income-tax returns (1701Q, 1702Q, 1701, 1701A, 1702-RT) computed in whole
pesos, exported in each form's own eBIRForms layout (the fixtures' key order,
byte for byte round-trippable), printed on their blanks, and fed from the books."""

import json
import os

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from ph_cas.birpdf import parse_ebir_export, render_return
from ph_cas.forms import f1701, f1701a, f1701q, f1702q, f1702rt
from ph_cas.forms import income as inc
from ph_cas.forms.engine import Context
from ph_cas.forms.export import ExportRefusal
from ph_cas.forms.period import parse as parse_period
from ph_cas.forms.registry import BUILT, spec
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.fixtures import make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_f1_2551q import TAXPAYER

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "birpdf", "fixtures")
INDIVIDUAL = dict(TAXPAYER, ph_taxpayer_type="Individual", ph_last_name="DELA CRUZ", ph_first_name="JUAN", ph_middle_name="M", ph_birthdate="1980-01-02", ph_civil_status="Married", ph_citizenship="Filipino", ph_individual_type="Professional")
MODULES = {"1701Q": (f1701q, "1701Q"), "1702Q": (f1702q, "1702Q"), "1701": (f1701, "1701"), "1701A": (f1701a, "1701A"), "1702-RT": (f1702rt, "1702RT")}


def ctx(form, period, company=None):
    c = dict(company or TAXPAYER, name=TEST_COMPANY, company_name=TEST_COMPANY)
    s = spec(form)
    return Context(s, parse_period(period, s.period), c, contact_number="09170000000", return_name="T")


def fixture_keys(key):
    with open(os.path.join(FIXTURES, f"{key}-sample.xml"), encoding="utf-8") as fh:
        return [k for k, _v in parse_ebir_export(fh.read())]


class TestG3Pure(IntegrationTestCase):
    def test_the_graduated_tables(self):
        self.assertEqual(inc.graduated_tax(250000, 2024), 0)
        self.assertEqual(inc.graduated_tax(300000, 2024), 7500)
        self.assertEqual(inc.graduated_tax(300000, 2022), 10000)
        self.assertEqual(inc.graduated_tax(1000000, 2024), 152500)
        self.assertEqual(inc.graduated_tax(10000000, 2024), 2902500)
        self.assertEqual(inc.graduated_tax(10000000, 2018), 3110000)
        self.assertEqual(str(inc.graduated_tax("500000.49", 2024)), "42500")

    def test_every_export_matches_its_fixture_key_order_and_round_trips(self):
        cases = [
            ("1701Q", "2026-Q2", INDIVIDUAL, {"atc": "II014", "salesA": "100000", "methodA": "osd", "spouseName": "X"}),
            ("1702Q", "2026-Q2", TAXPAYER, {"atc": "IC055", "s2_1": "100000"}),
            ("1701", "2026", INDIVIDUAL, {"atc": "II014", "salesA": "100000", "methodA": "itemized", "deductA": "1000", "compA": "5000"}),
            ("1701A", "2026", INDIVIDUAL, {"atc": "II014", "i36A": "100000"}),
            ("1702-RT", "2026", TAXPAYER, {"atc": "IC055", "i27": "100000", "rate": "20"}),
        ]
        for form, period, company, data in cases:
            self.assertIn(form, BUILT)
            mod, key = MODULES[form]
            c = ctx(form, period, company)
            rows, name = mod.export_rows(data, mod.compute(data, c), c)
            self.assertEqual([k for k, _v in rows], fixture_keys(key), form)
            text = mod.write_export(rows)
            back = parse_ebir_export(text)  # the parser decodes the encoded names; keys and the rest are verbatim
            self.assertEqual([k for k, _v in back], [k for k, _v in rows], form)
            self.assertTrue(all(f"<div>{k}={v}{k}=</div>" in text for k, v in rows), form)
            self.assertTrue(text.startswith("<?xml version='1.0'?>"), form)
            self.assertTrue(render_return(key, "2018-01", rows).startswith(b"%PDF"), form)
            self.assertTrue(name.startswith("123456789000"), name)
        self.assertEqual(name, "1234567890001702RTv2018122026.xml")

    def test_1701q_graduated_and_eight_percent(self):
        c = ctx("1701Q", "2026-Q1", INDIVIDUAL)
        data = {"atc": "II014", "salesA": "1000000", "cogsA": "200000", "methodA": "osd", "rateA": "graduated", "cwtA": "10000"}
        by = {ln["item"]: ln["amount"] for ln in f1701q.compute(data, c)}
        # eBIRForms: OSD is 40% of gross sales, so cost of sales closes at 0
        self.assertEqual((by["37A"], by["38A"], by["39/40A"], by["45A"], by["46A"], by["26A"], by["28/63A"]), (0, 1000000, 400000, 600000, 62500, 62500, 52500))
        rows = dict(f1701q.export_rows(data, f1701q.compute(data, c), c)[0])
        self.assertEqual(rows["frm1701q:txt40A"], "400,000.00")
        self.assertEqual(rows["frm1701q:txt39A"], "0.00")
        self.assertEqual(rows["frm1701q:DateQuarter_1"], "true")
        self.assertEqual(rows["frm1701q:optType_2"], "true")
        self.assertEqual(rows["frm1701q:txtTaxpayerName"], "DELA%20CRUZ%2C%20JUAN%2C%20M")
        self.assertEqual(rows["frm1701q:txtBirthYear"], "1980")
        data = {"atc": "II015", "salesA": "1000000", "rateA": "eight", "prev8A": "500000"}
        by = {ln["item"]: ln["amount"] for ln in f1701q.compute(data, ctx("1701Q", "2026-Q2", INDIVIDUAL))}
        self.assertEqual((by["51A"], by["53A"], by["54A"], by["26A"]), (1500000, 1250000, 100000, 100000))
        with self.assertRaises(ExportRefusal):
            c4 = ctx("1701Q", "2026-Q4", INDIVIDUAL)
            f1701q.export_rows(data, f1701q.compute(data, c4), c4)
        with self.assertRaises(ExportRefusal) as cm:
            bad = dict(data, atc="IC055")
            f1701q.export_rows(bad, f1701q.compute(bad, c), c)
        self.assertIn("Item 8", str(cm.exception))

    def test_1702q_mcit_and_1702rt_year(self):
        c = ctx("1702Q", "2026-Q3")
        data = {"atc": "IC055", "s2_1": "1000000", "s2_2": "400000", "s2_6": "100000", "s2_8": "200000", "sch4_5": "5000", "mcit": "yes"}
        by = {ln["item"]: ln["amount"] for ln in f1702q.compute(data, c)}
        self.assertEqual((by["Sch 2.9"], by["Sch 2.11"], by["Sch 2.12"], by["Sch 2.13"], by["25"]), (700000, 175000, 12000, 175000, 170000))
        rows = dict(f1702q.export_rows(data, f1702q.compute(data, c), c)[0])
        self.assertEqual(rows["frm1702q:rbQuarter_3"], "true")
        self.assertEqual(rows["frm1702q:Sched3:txtTax3"], "600,000.00")
        self.assertEqual(rows["frm1702q:Sched2:txtTax12"], "12,000.00")
        self.assertEqual(rows["frm1702q:rbMthdOfDdctns_1"], "true")
        # Item 5 takes one ATC: the regular tax (175,000) is higher, so IC010 alone is marked
        self.assertEqual((rows["frm1702q:rbATC_1"], rows["frm1702q:rbATC_2"], rows["frm1702q:cbATC_2"]), ("false", "true", "IC010_25%25"))
        data["mcit"] = "no"
        by = {ln["item"]: ln["amount"] for ln in f1702q.compute(data, c)}
        self.assertEqual(by["Sch 2.12"], 0)

    def test_item_5_takes_the_higher_tax_and_the_taxpayer_may_choose_the_regular_rate(self):
        c = ctx("1702Q", "2026-Q3")
        # a thin margin: regular tax 25,000 (25% of 100,000), MCIT 40,000 (2% of 2,000,000)
        data = {"s2_1": "2000000", "s2_2": "0", "s2_6": "1900000", "mcit": "yes"}
        by = {ln["item"]: ln["amount"] for ln in f1702q.compute(data, c)}
        self.assertEqual((by["Sch 2.11"], by["Sch 2.12"], by["Sch 2.13"], by["14"]), (25000, 40000, 40000, 40000))
        rows = dict(f1702q.export_rows(data, f1702q.compute(data, c), c)[0])
        self.assertEqual((rows["frm1702q:rbATC_1"], rows["frm1702q:rbATC_2"]), ("true", "false"))
        # both computations stay on the return
        self.assertEqual((rows["frm1702q:Sched2:txtTax11"], rows["frm1702q:Sched3:txtTax6"]), ("25,000.00", "40,000.00"))
        data["atcChoice"] = "regular"
        data["i15"] = "1000"
        by = {ln["item"]: ln["amount"] for ln in f1702q.compute(data, c)}
        self.assertEqual((by["Sch 2.13"], by["14"], by["15"], by["16"]), (25000, 25000, 1000, 24000))
        rows = dict(f1702q.export_rows(data, f1702q.compute(data, c), c)[0])
        self.assertEqual((rows["frm1702q:rbATC_1"], rows["frm1702q:rbATC_2"], rows["frm1702q:Sched3:txtTax6"]), ("false", "true", "40,000.00"))
        c = ctx("1702-RT", "2025")
        data = {"atc": "IC055", "i27": "100000", "i30": "0", "i34": "90000", "mcit": "yes", "presTitle": "President", "treasurer": "X"}
        by = {ln["item"]: ln["amount"] for ln in f1702rt.compute(data, c)}
        self.assertEqual((by["41"], by["42"], by["43"]), (2500, 2000, 2500))
        data["i34"] = "99000"
        by = {ln["item"]: ln["amount"] for ln in f1702rt.compute(data, c)}
        self.assertEqual((by["41"], by["42"], by["43"]), (250, 2000, 2000))
        rows = dict(f1702rt.export_rows(data, f1702rt.compute(data, c), c)[0])
        self.assertEqual((rows["frm1702RT:rdoPg1I5Atc"], rows["frm1702RT:rdoPg1I5AtcOther"]), ("true", "false"))
        data["atcChoice"] = "regular"
        rows = dict(f1702rt.export_rows(data, f1702rt.compute(data, c), c)[0])
        self.assertEqual((rows["frm1702RT:rdoPg1I5Atc"], rows["frm1702RT:rdoPg1I5AtcOther"], rows["frm1702RT:drpPg1I5AtcOther"], rows["frm1702RT:txtPg2Pt4I43TotalIncomeTax"]), ("false", "true", "IC010", "250.00"))
        c = ctx("1702-RT", "2026")
        data = {"atc": "IC055", "i27": "5000000", "i30": "3000000", "s1_13": "800000", "s1_5": "100000", "rate": "25", "i49": "40000", "mcit": "yes", "presTitle": "President", "treasurer": "X"}
        by = {ln["item"]: ln["amount"] for ln in f1702rt.compute(data, c)}
        self.assertEqual((by["34"], by["39"], by["41"], by["42"], by["43"], by["16"]), (900000, 1100000, 275000, 40000, 275000, 235000))
        rows = dict(f1702rt.export_rows(data, f1702rt.compute(data, c), c)[0])
        self.assertEqual(rows["frm1702RT:Pg2Pt4I40IncomeTaxRate"], "25%")
        self.assertEqual(rows["frm1702RT:txtPg1I2Year"], "26")
        self.assertEqual(rows["frm1702RT:txtPg2Pt4I28LessSales"], "0")
        self.assertEqual(rows["frm1702RT:txtPg3Sc1I13Salaries"], "800,000.00")
        self.assertEqual(rows["frm1702RT:txtPg1Pt1I8Name1"], "INVENTED%20SAMPLE%20TRADING")
        self.assertEqual(rows["frm1702RT:txtPg2RegisteredName"], "INVENTED SAMPLE TRADING")
        data = {"atc": "IC055", "i27": "100000", "i30": "90000", "mcit": "yes"}
        by = {ln["item"]: ln["amount"] for ln in f1702rt.compute(data, c)}
        self.assertEqual((by["41"], by["42"], by["43"]), (2500, 200, 2500))

    def test_1701_and_1701a_annual(self):
        c = ctx("1701", "2026", INDIVIDUAL)
        data = {"atc": "II014", "salesA": "2000000", "cogsA": "500000", "methodA": "itemized", "deductA": "300000", "compA": "600000", "compCwtA": "50000", "prevPaidA": "20000", "rateA": "graduated"}
        by = {ln["item"]: ln["amount"] for ln in f1701.compute(data, c)}
        self.assertEqual((by["Sch 3.24A"], by["22A"], by["23A"], by["24A"]), (1800000, 352500, 70000, 282500))
        rows = dict(f1701.export_rows(data, f1701.compute(data, c), c)[0])
        self.assertEqual(rows["frm1701:txtPg2IShed3_16A"], "300,000.00")
        self.assertEqual(rows["frm1701:rdoPg1I21AMethodDeductionI"], "true")
        self.assertEqual(rows["frm1701:chkPg2IShed1a_1Taxpayer"], "true")
        self.assertEqual(rows["frm1701:txtPg4IPart7_2A"], "20,000.00")
        self.assertEqual(rows["frm1701:txtPg1I33NumberOfAttachments"], "00")
        self.assertEqual(rows["frm1701:txtPg1I8TaxpayerName"], "DELA%20CRUZ%2C%20JUAN%20M")
        data = {"atc": "II016", "salesA": "2000000", "compA": "600000", "rateA": "eight"}
        by = {ln["item"]: ln["amount"] for ln in f1701.compute(data, c)}
        # eBIRForms: a mixed income earner on 8% gets no 250,000 reduction; compensation is taxed at the graduated rates
        self.assertEqual((by["Sch 3.30A"], by["Part VI.1A"], by["22A"]), (2000000, 222500, 222500))
        needs = [n.key for n in f1701.needs(data, c)]
        self.assertIn("data.spouseIncome", needs)
        c = ctx("1701A", "2026", INDIVIDUAL)
        data = {"atc": "II014", "i36A": "1000000", "taxRate": "graduated", "i60A": "5000", "spouseIncome": "no", "filing": "separate"}
        by = {ln["item"]: ln["amount"] for ln in f1701a.compute(data, c)}
        self.assertEqual((by["39A"], by["45A"], by["46A"], by["20A"], by["22A"]), (400000, 600000, 62500, 62500, 57500))
        rows = dict(f1701a.export_rows(data, f1701a.compute(data, c), c)[0])
        self.assertEqual(rows["frm1701A:txtBirthDate"], "01/02/1980")
        self.assertEqual(rows["frm1701A:optFilingStatus_2"], "true")
        self.assertEqual(rows["frm1701A:txtVersion"], "11112018")
        self.assertEqual(rows["txtEnroll"], "N")
        self.assertEqual(f1701a.write_export(list(rows.items()))[-5:], "2014.")


class TestG3Books(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        self.fields = dict(TAXPAYER, ph_income_tax_option="Corporate", ph_deduction_method="Itemized", ph_corp_small=0, ph_operations_start_year=0)
        self.saved = {k: frappe.db.get_value("Company", TEST_COMPANY, k) for k in self.fields}
        frappe.db.set_value("Company", TEST_COMPANY, self.fields, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        frappe.clear_cache(doctype="Company")
        self.qs, self.qe = quarter_bounds(today())
        self.q = f"{self.qs.year}-Q{(self.qs.month - 1) // 3 + 1}"
        for form in ("1702Q", "1702-RT"):
            for n in frappe.get_all("PH Tax Return", {"company": TEST_COMPANY, "form": form, "docstatus": 0}, pluck="name"):
                frappe.delete_doc("PH Tax Return", n, force=True, ignore_permissions=True)

    def tearDown(self):
        frappe.db.set_value("Company", TEST_COMPANY, self.saved, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        frappe.clear_cache(doctype="Company")

    def test_1702q_and_1702rt_from_the_books(self):
        make_sales_invoice(rate=10000)
        if self.q.endswith("Q4"):
            self.q = self.q[:-1] + "3"
        q = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "1702Q", "period_key": self.q}).insert()
        q.refresh_from_books()
        q.reload()
        d = json.loads(q.data)
        self.assertEqual(d["rate"], "25")
        self.assertEqual(d["method"], "itemized")
        self.assertEqual(d["mcit"], "no")
        by = {r.item: (flt(r.amount), r.source) for r in q.lines}
        self.assertEqual(by["Sch 2.1"][1], "books")
        self.assertEqual(by["Sch 2.5"][1], "derived")
        q.set_inputs(json.dumps({"atc": "IC055"}))
        q.reload()
        url = q.export_for_ebirforms()
        self.assertTrue(url.endswith(f"-1702Qv2018C-{self.qs.year}Q{self.q[-1]}.xml"))
        content = frappe.get_doc("File", {"file_url": url}).get_content()
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        self.assertTrue(text.startswith("<?xml version='1.0'?>\t\r\n"))
        self.assertTrue(text.endswith("All Rights Reserved BIR 2012.0"))
        self.assertIn("DRAFT", q.preview())
        a = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "1702-RT", "period_key": str(self.qs.year)}).insert()
        a.refresh_from_books()
        a.reload()
        d = json.loads(a.data)
        self.assertGreaterEqual(flt(d["i27"]), 10000)
        self.assertIn("i34", d)
        by = {r.item: (flt(r.amount), r.source) for r in a.lines}
        self.assertEqual(by["27"][1], "books")
        self.assertEqual(by["43"][1], "derived")
        needs = [n["key"] for n in json.loads(a.needs)]
        self.assertIn("data.atc", needs)
        self.assertIn("data.presTitle", needs)
