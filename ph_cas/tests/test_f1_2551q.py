"""F1: the 2551Q end to end. Books feed into Schedule 1, compute in whole pesos,
the eBIRForms file in the package's layout, the DRAFT preview on the blank,
the confirmation e-mail, the filing (sealed, snapshot, clear copy, figures
published) and the amendment a manager opens."""

import io
import os
import json
from datetime import date

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, getdate, today
from pypdf import PdfReader

from ph_cas.birpdf import parse_ebir_export
from ph_cas.forms import f2551q
from ph_cas.forms.engine import Context
from ph_cas.forms.period import parse as parse_period
from ph_cas.forms.registry import spec
from ph_cas.ph_cas.doctype.ph_tax_return.ph_tax_return import attach_confirmation
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _item, _set_regime

TAXPAYER = {
    "tax_id": "123-456-789",
    "ph_branch_code": "00000",
    "ph_rdo": "044",
    "ph_registered_name": "INVENTED SAMPLE TRADING",
    "ph_taxpayer_type": "Non-individual",
    "ph_registered_address": "12 INVENTED STREET, BARANGAY HALIMBAWA, LUNGSOD NG HALIMBAWA",
    "ph_zip": "1234",
    "ph_contact_number": "09170000000",
    "ph_email": "accounts@invented-sample.example",
    "ph_pt_atc": "PT010",
}


def ctx_for(data_period: str = "2026-Q1") -> Context:
    c = dict(TAXPAYER, name=TEST_COMPANY, company_name=TEST_COMPANY)
    return Context(spec("2551Q"), parse_period(data_period, "quarter"), c, return_name="T")


class TestF1Compute(IntegrationTestCase):
    """Pure: no books."""

    def test_schedule_rows_round_to_whole_pesos_and_items_flow(self):
        data = {"rows": [{"atc": "PT010", "taxable": "10016", "rate": "3.0"}, {"atc": "PT040", "taxable": "1000.00", "rate": "3"}], "i15": "100", "i20": "25", "over": ""}
        lines = f2551q.compute(data, ctx_for())
        by = {ln["item"]: ln["amount"] for ln in lines}
        self.assertEqual(by["S1.1 tax"], 300)  # 300.48 drops
        self.assertEqual(by["S1.2 tax"], 30)
        self.assertEqual(by["14"], 330)
        self.assertEqual(by["18"], 100)
        self.assertEqual(by["19"], 230)
        self.assertEqual(by["23"], 25)
        self.assertEqual(by["24"], 255)

    def test_needs_and_refusals(self):
        c = ctx_for()
        data = {"rows": [{"atc": "", "taxable": "500", "rate": "3"}], "i15": "900"}
        keys = [n.key for n in f2551q.needs(data, c)]
        self.assertIn("data.rows.1.atc", keys)
        self.assertIn("data.over", keys)  # overpayment with no choice
        with self.assertRaises(Exception) as cm:
            f2551q.export_rows(data, f2551q.compute(data, c), c)
        self.assertIn("no ATC", str(cm.exception))
        data = {"rows": [{"atc": "PT999", "taxable": "500", "rate": "3"}]}
        self.assertIn("data.rows.1.atc", [n.key for n in f2551q.needs(data, c)])

    def test_export_matches_the_package_keys_and_the_overlay_prints_it(self):
        c = ctx_for()
        data = {"rows": [{"atc": "PT010", "taxable": "100000", "rate": "3.0"}], "i15": "1000", "taxAgentNo": "", "over": ""}
        rows, name = f2551q.export_rows(data, f2551q.compute(data, c), c)
        self.assertEqual(name, "1234567890002551Qv2018122026Q1.xml")
        d = dict(rows)
        self.assertEqual(d["frm2551Qv2018:qtr_1"], "true")
        self.assertEqual(d["frm2551Qv2018:txtTIN1"], "123")
        self.assertEqual(d["frm2551Qv2018:txtBranchCode"], "000")
        self.assertEqual(d["frm2551Qv2018:registeredName"], "INVENTED%20SAMPLE%20TRADING")
        self.assertEqual(d["frm2551Qv2018:txt14"], "3,000.00")
        self.assertEqual(d["frm2551Qv2018:txt24"], "2,000.00")
        self.assertEqual(d["drpATC1"], "1")
        self.assertEqual(d["txtATCRate1"], "3.0")
        self.assertEqual(d["txtATCDue1"], "3,000.00")
        self.assertEqual(d["drpATC2"], "0")
        self.assertEqual(d["txtFinalFlag"], "0")
        self.assertEqual(rows[-1][0], "driveSelectTPExport")
        # the same keys as the Portal's real export fixture, in the same order
        fixture = parse_ebir_export(open(os.path.join(frappe.get_app_path("ph_cas"), "birpdf", "fixtures", "2551Q-sample.xml"), encoding="utf-8").read())
        self.assertEqual([k for k, _ in rows], [k for k, _ in fixture])
        from ph_cas.birpdf import render_return
        from ph_cas.forms.export import write_tabbed

        pdf = render_return("2551Q", "2018-01", parse_ebir_export(write_tabbed(rows)))
        self.assertTrue(pdf.startswith(b"%PDF"))


class TestF1EndToEnd(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("Non-VAT")
        self.saved = {k: frappe.db.get_value("Company", TEST_COMPANY, k) for k in TAXPAYER}
        frappe.db.set_value("Company", TEST_COMPANY, TAXPAYER, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        frappe.clear_cache(doctype="Company")
        self.qs, self.qe = quarter_bounds(today())
        self.period = f"{self.qs.year}-Q{(self.qs.month - 1) // 3 + 1}"
        for n in frappe.get_all("PH Tax Return", {"company": TEST_COMPANY, "form": "2551Q"}, pluck="name"):
            frappe.db.sql("delete from `tabPH Tax Return Line` where parent = %s", n)
            frappe.db.sql("delete from `tabPH Tax Return` where name = %s", n)
        frappe.db.sql("delete from `tabPH BIR Confirmation` where tin = %s", TAXPAYER["tax_id"])

    def tearDown(self):
        frappe.db.set_value("Company", TEST_COMPANY, self.saved, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        frappe.clear_cache(doctype="Company")

    def _confirmation_text(self, received="25 April 2026"):
        return (
            "From: eBIRForms <ebirforms-noreply@bir.gov.ph>\nSubject: Tax Return Receipt Confirmation\n\n"
            "This confirms receipt of your submission with the following details:\n"
            f"File name: 123456789000-2551Qv2018-12{self.qs.year}Q{(self.qs.month - 1) // 3 + 1}.xml\n"
            f"Date received by BIR: {received}\nTime received by BIR: 11:40 AM\n"
        )

    def test_books_to_filed_return_to_amendment(self):
        _invoice([(_item("_PH VATable", "VATable"), 1, 10000, {})], submit=True)
        doc = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "2551Q", "period_key": self.period}).insert()
        self.assertEqual(doc.status, "Ready", doc.needs)
        doc.refresh_from_books()
        doc.reload()
        data = json.loads(doc.data)
        self.assertEqual(data["rows"][0]["atc"], "PT010")
        self.assertGreaterEqual(int(float(data["rows"][0]["taxable"])), 10000)
        self.assertEqual(data["_source"]["kind"], "books")
        by = {r.item: (flt(r.amount), r.source) for r in doc.lines}
        self.assertEqual(by["S1.1 base"][1], "books")
        self.assertEqual(by["14"][1], "derived")
        self.assertEqual(by["14"][0], flt(round(by["S1.1 base"][0] * 0.03)))
        # a hand change to a books figure is kept and flagged on the next refresh
        data["i15"] = "7"
        doc.data = json.dumps(data)
        doc.save()
        doc.refresh_from_books()
        doc.reload()
        self.assertEqual(json.loads(doc.data)["i15"], "7")
        self.assertIn("changed by hand", doc.warnings)
        # export and preview
        url = doc.export_for_ebirforms()
        self.assertTrue(url.endswith(".xml"))
        doc.reload()
        self.assertEqual(doc.export_file_name, f"1234567890002551Qv201812{self.qs.year}Q{(self.qs.month - 1) // 3 + 1}.xml")
        content = frappe.get_doc("File", {"file_url": doc.export_file}).get_content()
        self.assertTrue(content.startswith("<?xml version='1.0'?>\t\t<div>frm2551Qv2018:forThe_1=true"))
        self.assertIn("txtFinalFlag=0txtFinalFlag=", content)
        preview = doc.preview()
        self.assertTrue(preview.endswith("DRAFT.pdf"))
        pdf = frappe.get_doc("File", {"file_url": preview}).get_content()
        text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
        self.assertIn("NOT FILED", text)
        # filing needs the confirmation
        with self.assertRaises(frappe.ValidationError):
            doc.submit()
        doc.reload()
        f = frappe.get_doc({"doctype": "File", "file_name": "confirmation.txt", "is_private": 1, "content": self._confirmation_text()}).insert()
        out = attach_confirmation(doc.name, f.file_url)
        self.assertEqual(out["errors"], [])
        doc.reload()
        self.assertTrue(doc.confirmation)
        doc.submit()
        doc.reload()
        self.assertEqual((doc.docstatus, doc.status), (1, "Filed"))
        self.assertEqual(str(doc.filed_on), "2026-04-25")
        self.assertTrue(doc.clear_copy and doc.clear_copy.endswith("as filed.pdf"))
        snap = json.loads(doc.filed_snapshot)
        self.assertEqual(snap["company"]["tax_id"], "123-456-789")
        filed_export = frappe.get_doc("File", {"file_url": doc.export_file}).get_content()
        self.assertIn("txtFinalFlag=1txtFinalFlag=", filed_export)
        fig = frappe.get_doc("PH Tax Return Figures", {"company": TEST_COMPANY, "form": "2551Q", "period_label": self.period})
        self.assertEqual(fig.filed, 1)
        self.assertEqual(fig.figure("14"), by["14"][0])
        self.assertEqual(fig.figure("24"), by["24"][0] - 7)
        # sealed
        with self.assertRaises(frappe.ValidationError):
            doc.refresh_from_books()
        with self.assertRaises(Exception):
            frappe.delete_doc("PH Tax Return", doc.name)
        # the snapshot, not the live company, feeds later prints
        frappe.db.set_value("Company", TEST_COMPANY, "ph_registered_name", "RENAMED LATER", update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        self.assertEqual(frappe.get_doc("PH Tax Return", doc.name)._company()["ph_registered_name"], "INVENTED SAMPLE TRADING")
        # a manager opens the amendment
        amended = frappe.get_doc("PH Tax Return", doc.open_amendment("Found a missed invoice"))
        self.assertEqual((amended.amends, amended.is_amended, amended.docstatus), (doc.name, 1, 0))
        self.assertTrue(amended.name.endswith("-A1"))
        amended.refresh_from_books()
        amended.reload()
        filed_24 = flt(frappe.db.get_value("PH Tax Return Line", {"parent": doc.name, "item": "24"}, "amount"))
        self.assertEqual(filed_24, by["24"][0] - 7)
        self.assertEqual(flt(json.loads(amended.data)["i16"]), filed_24)
        rows, _n = f2551q.export_rows(json.loads(amended.data), f2551q.compute(json.loads(amended.data), amended._ctx()), amended._ctx())
        self.assertEqual(dict(rows)["frm2551Qv2018:amendedRtn_1"], "true")

    def test_a_wrong_confirmation_is_named(self):
        doc = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "2551Q", "period_key": self.period}).insert()
        wrong = self._confirmation_text().replace("2551Qv2018", "2550Qv2024")
        f = frappe.get_doc({"doctype": "File", "file_name": "wrong.txt", "is_private": 1, "content": wrong}).insert()
        out = attach_confirmation(doc.name, f.file_url)
        self.assertTrue(any("2550Q" in e for e in out["errors"]))
        doc.reload()
        with self.assertRaises(frappe.ValidationError) as cm:
            doc.submit()
        self.assertIn("does not match", str(cm.exception))
