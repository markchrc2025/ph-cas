"""G2: the withholding forms printed on their blanks: 0619-E, 1601-EQ with its QAP,
and the 2307 certificates (one page each, from PH 2307 Issued)."""

import io
import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_months, flt, get_first_day, today
from pypdf import PdfReader

from ph_cas.birpdf import render_return
from ph_cas.forms import f0619e, f1600vt, f1601eq, f1604e, f2307
from ph_cas.forms.engine import Context
from ph_cas.forms.export import ExportRefusal
from ph_cas.forms.period import parse as parse_period
from ph_cas.forms.registry import spec
from ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued import generate_quarter, print_bir_form
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.fixtures import ensure_service_item, ensure_supplier_profile, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_f1_2551q import TAXPAYER


def ctx(form, period):
    c = dict(TAXPAYER, name=TEST_COMPANY, company_name=TEST_COMPANY)
    s = spec(form)
    return Context(s, parse_period(period, s.period), c, contact_number="09170000000", return_name="T")


class TestG2Pure(IntegrationTestCase):
    def test_0619e_rows_print_centavos_and_refuse_negatives(self):
        c = ctx("0619-E", "2026-01")
        data = {"remittance": "1234.56", "previouslyRemitted": "0", "surcharge": "10", "interest": "0.5", "compromise": "0", "signatoryName": "JUAN DELA CRUZ", "signatoryTitle": "Owner", "signatoryTin": "123456789", "anyWithheld": "yes"}
        comp = f0619e.compute(data, c)
        by = {ln["item"]: ln["amount"] for ln in comp}
        self.assertEqual(str(by["16"]), "1234.56")
        self.assertEqual(str(by["17D"]), "10.50")
        self.assertEqual(str(by["18"]), "1245.06")
        rows = dict(f0619e.print_rows(data, comp, c))
        self.assertEqual(rows["f0619E:month"], "012026")
        self.assertEqual(rows["f0619E:dueDate"], "02/10/2026")
        self.assertEqual(rows["f0619E:i18"], "1245.06")
        self.assertEqual(rows["f0619E:branch"], "00000")
        self.assertEqual(rows["f0619E:amendedNo"], "true")
        self.assertEqual(rows["f0619E:sigNonTitleTin"], "Owner / TIN 123-456-789")
        pdf = render_return("0619E", "2018-01", list(rows.items()))
        self.assertTrue(pdf.startswith(b"%PDF"))
        data["remittance"] = "-5"
        with self.assertRaises(ExportRefusal) as cm:
            f0619e.print_rows(data, f0619e.compute(data, c), c)
        self.assertIn("Item 14", str(cm.exception))

    def test_1601eq_rows_over_remittance_and_six_rows(self):
        c = ctx("1601-EQ", "2026-Q2")
        data = {"rows": [{"atc": "WC120", "base": "10000", "rate": "2", "withheld": "200"}, {"atc": "WI100", "base": "5000", "rate": "5", "withheld": "250"}], "remittance1": "300", "remittance2": "300", "signatoryName": "X"}
        comp = f1601eq.compute(data, c)
        by = {ln["item"]: ln["amount"] for ln in comp}
        self.assertEqual(str(by["19"]), "450.00")
        self.assertEqual(str(by["26"]), "-150.00")
        self.assertIn("data.overRemittanceChoice", [n.key for n in f1601eq.needs(data, c)])
        with self.assertRaises(ExportRefusal):
            f1601eq.print_rows(data, comp, c)
        data["overRemittanceChoice"] = "carried"
        rows = dict(f1601eq.print_rows(data, f1601eq.compute(data, c), c))
        self.assertEqual(rows["f1601EQ:q2"], "true")
        self.assertEqual(rows["f1601EQ:i26"], "150.00")
        self.assertEqual(rows["f1601EQ:overCarried"], "true")
        self.assertEqual(rows["f1601EQ:r1Rate"], "2%")
        self.assertEqual(rows["f1601EQ:p2Tin"], "12345678900000")
        self.assertTrue(render_return("1601EQ", "2019-01", list(rows.items())).startswith(b"%PDF"))
        # carried is not a choice in the fourth quarter
        c4 = ctx("1601-EQ", "2026-Q4")
        self.assertIn("data.overRemittanceChoice", [n.key for n in f1601eq.needs(data, c4)])
        data["rows"] = [{"atc": f"WC{i}", "base": "1", "rate": "1", "withheld": "0.01"} for i in range(7)]
        with self.assertRaises(ExportRefusal) as cm:
            f1601eq.print_rows(data, f1601eq.compute(data, c), c)
        self.assertIn("room for 6", str(cm.exception))


    def test_1600vt_and_1604e_print_on_their_new_maps(self):
        c = ctx("1600-VT", "2026-03")
        data = {"rows": [{"atc": "WV010", "base": "100000", "rate": "5", "withheld": "5000"}], "signatoryName": "X", "anyWithheld": "yes", "payCashBank": "LANDBANK", "payCashDate": "2026-04-10", "payCashAmount": "5000"}
        rows = dict(f1600vt.print_rows(data, f1600vt.compute(data, c), c))
        self.assertEqual(rows["f1600VT:month"], "03")
        self.assertEqual(rows["f1600VT:year"], "2026")
        self.assertEqual(rows["f1600VT:r1Rate"], "5")
        self.assertEqual(rows["f1600VT:i27"], "5000.00")
        pdf = render_return("1600VT", "2018-01", list(rows.items()))
        self.assertEqual(len(PdfReader(io.BytesIO(pdf)).pages), 2)
        c = ctx("1604-E", "2026")
        data = {"sch1": [{"q": "1", "date": "2026-04-30", "bank": "LANDBANK", "number": "123", "withheld": "1500.50", "penalties": "0", "total": "1500.50"}], "topAgent": "no", "signatoryName": "X"}
        rows = dict(f1604e.print_rows(data, f1604e.compute(data, c), c))
        self.assertEqual(rows["f1604E:year"], "2026")
        self.assertEqual(rows["f1604E:s1q1Date"], "04/30/2026")
        self.assertEqual(rows["f1604E:s1TotalWithheld"], "1500.50")
        self.assertEqual(rows["f1604E:topNo"], "true")
        self.assertTrue(render_return("1604E", "2018-01", list(rows.items())).startswith(b"%PDF"))


class TestG2Books(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        self.saved = {k: frappe.db.get_value("Company", TEST_COMPANY, k) for k in TAXPAYER}
        frappe.db.set_value("Company", TEST_COMPANY, TAXPAYER, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        frappe.clear_cache(doctype="Company")
        self.qs, self.qe = quarter_bounds(today())
        self.q = f"{self.qs.year}-Q{(self.qs.month - 1) // 3 + 1}"
        self.sup = ensure_supplier_profile("_Test PH Contractor", ph_vat_status="Non-VAT", ph_payee_type="Non-individual", ph_ewt_category="contractor")
        frappe.db.set_value("Supplier", self.sup, {"tax_id": "987-654-321", "ph_registered_name": "INVENTED CONTRACTOR CORP"}, update_modified=False)
        frappe.clear_document_cache("Supplier", self.sup)
        for form in ("0619-E", "1601-EQ", "2307"):
            for n in frappe.get_all("PH Tax Return", {"company": TEST_COMPANY, "form": form}, pluck="name"):
                frappe.db.sql("delete from `tabPH Tax Return Line` where parent = %s", n)
                frappe.db.sql("delete from `tabPH Tax Return` where name = %s", n)

    def tearDown(self):
        frappe.db.set_value("Company", TEST_COMPANY, self.saved, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        frappe.clear_cache(doctype="Company")

    def test_0619e_and_1601eq_from_the_books_with_qap(self):
        make_purchase_invoice(self.sup, [(ensure_service_item(), 1, 5000, {})], submit=True)
        m = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "0619-E", "period_key": today()[:7]}).insert()
        m.refresh_from_books()
        m.reload()
        d = json.loads(m.data)
        self.assertGreaterEqual(flt(d["remittance"]), 100)
        by = {r.item: (flt(r.amount), r.source) for r in m.lines}
        self.assertEqual(by["14"][1], "books")
        self.assertEqual(by["18"][1], "derived")
        if get_first_day(today()).month % 3 != 0:
            m.set_inputs(json.dumps({"signatoryName": "X", "signatoryTitle": "Owner"}))
            m.reload()
            self.assertIn("DRAFT", m.preview())
        q = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "1601-EQ", "period_key": self.q}).insert()
        q.refresh_from_books()
        q.reload()
        d = json.loads(q.data)
        self.assertTrue(any(r["atc"] == "WC120" for r in d["rows"]))
        by = {r.item: (flt(r.amount), r.source) for r in q.lines}
        self.assertGreaterEqual(by["19"][0], 100)
        q.set_inputs(json.dumps({"signatoryName": "X", "overRemittanceChoice": "tcc"}))
        q.reload()
        self.assertIn("DRAFT", q.preview())
        names = q.generate_attachment()  # one QAP per month with payees (B62)
        name = names[-1]
        self.assertTrue(frappe.db.exists("PH Alphalist File", name))
        q.reload()
        self.assertEqual(q.alphalist_file, name)
        content = frappe.get_doc("File", {"file_url": frappe.db.get_value("PH Alphalist File", name, "file_url")}).get_content()
        self.assertTrue(content.startswith("HQAP,H1601EQ"))
        self.assertIn("WC120", content)

    def test_2307_certificates_print_one_page_each(self):
        make_purchase_invoice(self.sup, [(ensure_service_item(), 1, 10000, {})], submit=True)
        names = generate_quarter(TEST_COMPANY, str(self.qs))
        self.assertTrue(names)
        cert = frappe.get_doc("PH 2307 Issued", names[0])
        if cert.docstatus == 0:
            cert.submit()
        url = print_bir_form(cert.name)
        self.assertIn("BIR 2307", url)
        pdf = frappe.get_doc("File", {"file_url": url}).get_content()
        self.assertEqual(len(PdfReader(io.BytesIO(pdf)).pages), 1)
        run = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "2307", "period_key": self.q}).insert()
        run.refresh_from_books()
        run.reload()
        self.assertIn(cert.name, json.loads(run.data)["certificates"])
        prev = run.preview()
        self.assertIn("DRAFT", prev)
        pages = PdfReader(io.BytesIO(frappe.get_doc("File", {"file_url": prev}).get_content())).pages
        self.assertEqual(len(pages), len(json.loads(run.data)["certificates"]))
        text = pages[0].extract_text()
        self.assertIn("NOT FILED", text)
        # the run is issued (submitted) without a BIR confirmation
        run.submit()
        run.reload()
        self.assertEqual((run.docstatus, run.filed_reference), (1, "issued"))
        self.assertTrue(run.clear_copy)
