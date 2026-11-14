"""G1: the 2550Q end to end (feed from the VAT engine, compute, export keys in the
Portal's order, print), the inputs editor's server side, and the SLSP tie-out."""

import json
import os

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from ph_cas.birpdf import parse_ebir_export, render_return
from ph_cas.forms import f2550q
from ph_cas.forms.engine import Context
from ph_cas.forms.export import write_lined
from ph_cas.forms.period import parse as parse_period
from ph_cas.forms.registry import spec
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _item, _set_regime
from ph_cas.tests.test_f1_2551q import TAXPAYER


def ctx_for(period="2026-Q1", fiscal=None) -> Context:
    c = dict(TAXPAYER, name=TEST_COMPANY, company_name=TEST_COMPANY, ph_taxpayer_class="Small", ph_fiscal_year_start=fiscal)
    return Context(spec("2550Q"), parse_period(period, "quarter", fiscal), c, return_name="T")


class TestG1Compute(IntegrationTestCase):
    def test_items_flow_and_schedules_feed_their_items(self):
        data = {
            "i31a": "100000", "i32a": "0", "i33a": "20000", "i38": "500",
            "i44a": "50000", "i44b": "6000", "i48a": "1000",
            "sch1": [{"c0": "01/15/2026", "c1": "S", "c2": "MACHINE", "c3": "2000000", "c4": "240000", "c5": "60", "c6": "3", "c7": "12000", "c8": "228000"}],
            "sch3": [{"c0": "01/01/2026", "c1": "GOV AGENCY", "c2": "10000", "c3": "500"}],
            "sch2_ratable": "1000", "i22": "0",
        }
        o = f2550q._o(f2550q.compute(data, ctx_for()))
        self.assertEqual(o["i31b"], 12000)
        self.assertEqual(o["i34a"], 120000)
        self.assertEqual(o["i39"], 240000)  # Schedule 1 Col E feeds 39
        self.assertEqual(o["i43"], 240500)
        self.assertEqual(o["i50b"], 6000)
        self.assertEqual(o["i51"], 246500)
        self.assertEqual(o["i52"], 228000)  # Col I feeds 52
        self.assertEqual(o["i53"], 1000)
        self.assertEqual(o["i57"], 229000)
        self.assertEqual(o["i60"], 17500)
        self.assertEqual(o["i61"], 12000 - 17500)
        self.assertEqual(o["i16"], 500)  # Schedule 3 Col D feeds 16
        self.assertEqual(o["i21"], o["i15"] - 500)
        self.assertEqual(o["i26"], o["i21"])

    def test_export_keys_match_the_portal_fixture_and_print(self):
        c = ctx_for()
        data = {"i31a": "100000", "i44a": "50000", "i44b": "6000", "classification": "Small"}
        rows, name = f2550q.export_rows(data, f2550q.compute(data, c), c)
        self.assertEqual(name, "1234567890002550Qv2024122026Q1.xml")
        d = dict(rows)
        self.assertEqual(d["frm2550qv2024:calendarNo1"], "true")
        self.assertEqual(d["frm2550qv2024:selectedMonthNo2"], "12")
        self.assertEqual(d["frm2550qv2024:RtnPeriodFromNo4"], "1/01/2026")
        self.assertEqual(d["frm2550qv2024:RtnPeriodToNo4"], "3/31/2026")
        self.assertEqual(d["frm2550qv2024:taxPayerClassification2"], "true")
        self.assertEqual(d["frm2550qv2024:outputVatSales"], "12,000.00")
        self.assertEqual(d["frm2550qv2024:netVatPayable"], "6,000.00")
        self.assertEqual(d["dateFiled"], c.date_filed or "")
        fixture = parse_ebir_export(open(os.path.join(frappe.get_app_path("ph_cas"), "birpdf", "fixtures", "2550Q-sample.xml"), encoding="utf-8").read())
        self.assertEqual([k for k, _ in rows], [k for k, _ in fixture])
        pdf = render_return("2550Q", "2024-04", parse_ebir_export(write_lined(rows)))
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_fiscal_year_shapes_the_return(self):
        c = ctx_for("2026-Q1", "2025-07-01")
        rows, name = f2550q.export_rows({}, f2550q.compute({}, c), c)
        d = dict(rows)
        self.assertEqual(d["frm2550qv2024:fiscalNo1"], "true")
        self.assertEqual(d["frm2550qv2024:selectedMonthNo2"], "06")
        self.assertEqual(d["frm2550qv2024:RtnPeriodFromNo4"], "7/01/2025")
        self.assertEqual(d["frm2550qv2024:RtnPeriodToNo4"], "9/30/2025")
        self.assertEqual(name, "1234567890002550Qv2024062026Q1.xml")

    def test_needs_and_row_refusal(self):
        c = ctx_for()
        c.company["ph_taxpayer_class"] = ""
        data = {"sch3": [{"c1": "A", "c3": "1"}, {"c1": "B", "c3": "1"}, {"c1": "C", "c3": "1"}], "i42": "5", "taxRelief": "yes"}
        keys = [n.key for n in f2550q.needs(data, c)]
        for k in ("data.classification", "data.sch3", "data.i42label", "data.reliefKind", "data.taxReliefSpec"):
            self.assertIn(k, keys)
        with self.assertRaises(Exception) as cm:
            f2550q.export_rows(data, f2550q.compute(data, c), c)
        self.assertIn("Schedule 3", str(cm.exception))


class TestG1EndToEnd(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")
        self.saved = {k: frappe.db.get_value("Company", TEST_COMPANY, k) for k in TAXPAYER}
        frappe.db.set_value("Company", TEST_COMPANY, dict(TAXPAYER, ph_taxpayer_class="Small"), update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        frappe.clear_cache(doctype="Company")
        self.qs, self.qe = quarter_bounds(today())
        self.period = f"{self.qs.year}-Q{(self.qs.month - 1) // 3 + 1}"
        for n in frappe.get_all("PH Tax Return", {"company": TEST_COMPANY, "form": "2550Q"}, pluck="name"):
            frappe.db.sql("delete from `tabPH Tax Return Line` where parent = %s", n)
            frappe.db.sql("delete from `tabPH Tax Return` where name = %s", n)

    def tearDown(self):
        _set_regime("Non-VAT")
        frappe.db.set_value("Company", TEST_COMPANY, self.saved, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        frappe.clear_cache(doctype="Company")

    def test_books_feed_inputs_editor_and_slsp(self):
        _invoice([(_item("_PH VATable", "VATable"), 1, 10000, {})], submit=True)
        doc = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "2550Q", "period_key": self.period}).insert()
        doc.refresh_from_books()
        doc.reload()
        data = json.loads(doc.data)
        self.assertGreaterEqual(int(float(data["i31a"])), 10000)
        by = {r.item: (flt(r.amount), r.source) for r in doc.lines}
        self.assertEqual(by["31A"][1], "books")
        self.assertEqual(by["31B"][1], "derived")
        self.assertEqual(by["31B"][0], flt(round(by["31A"][0] * 0.12)))
        # the inputs editor's server side
        spec_ = doc.form_spec()
        self.assertTrue(spec_["built"])
        self.assertIn("i31a", spec_["books"])
        self.assertTrue(any(k == "i22" for k, _l, _t in spec_["inputs"]))
        self.assertEqual(spec_["schedules"]["sch3"]["keys"], ["c0", "c1", "c2", "c3"])
        doc.set_inputs(json.dumps({"i22": "100", "sch4": [{"c0": "01/02/2026", "c1": "MILLER", "c2": "T", "c3": "OR1", "c4": "250"}]}))
        doc.reload()
        by = {r.item: (flt(r.amount), r.source) for r in doc.lines}
        self.assertEqual(by["22"], (100.0, "typed"))
        self.assertEqual(by["17"], (250.0, "derived"))
        self.assertEqual(by["25"][0], 100.0)
        # export and preview
        doc.export_for_ebirforms()
        doc.reload()
        self.assertTrue(doc.export_file_name.endswith(f"2550Qv202412{self.qs.year}Q{(self.qs.month - 1) // 3 + 1}.xml"))
        content = frappe.get_doc("File", {"file_url": doc.export_file}).get_content()
        self.assertTrue(content.startswith("<?xml version='1.0'?>        <div>frm2550qv2024:calendarNo1=true"))
        self.assertIn("\n<div>frm2550qv2024:fiscalNo1=false", content)
        self.assertIn("DRAFT", doc.preview())
        # SLSP files and the tie-out
        out = doc.generate_slsp()
        self.assertEqual(len(out["files"]), 9)  # S, P and I for each month of the quarter (RDO answer 11)
        doc.reload()
        if doc.alphalist_file:
            self.assertTrue(frappe.db.exists("PH Alphalist File", doc.alphalist_file))
        self.assertIsInstance(out["tie_out"], list)
