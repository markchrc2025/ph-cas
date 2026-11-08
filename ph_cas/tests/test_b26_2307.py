"""B26: the 2307 issued to suppliers."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued import generate_quarter
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.fixtures import ensure_service_item, ensure_supplier_profile, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY


class TestB26_2307(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        self.qs, self.qe = quarter_bounds(today())
        self.sup = ensure_supplier_profile("_Test PH 2307 Payee", ph_vat_status="Non-VAT", ph_payee_type="Individual", ph_last_name="Santos", ph_first_name="Maria", ph_middle_name="Cruz", ph_tin="555-666-777", ph_ewt_category="rent", ph_address_line1="7 Mabini St", ph_zip="1800")
        for d in frappe.get_all("PH 2307 Issued", filters={"supplier": self.sup, "docstatus": ("<", 2)}, pluck="name"):
            doc = frappe.get_doc("PH 2307 Issued", d)
            if doc.docstatus == 1:
                doc.cancel()
            else:
                doc.delete()

    def test_generation_groups_by_atc_and_month(self):
        make_purchase_invoice(self.sup, [(ensure_service_item(), 1, 10000, {})], submit=True)
        make_purchase_invoice(self.sup, [(ensure_service_item(), 1, 5000, {})], submit=True)
        names = generate_quarter(TEST_COMPANY, str(self.qs))
        doc = frappe.get_doc("PH 2307 Issued", f"2307-{self.qs.year}-Q{(self.qs.month - 1) // 3 + 1}-{self.sup}")
        self.assertIn(doc.name, names)
        self.assertEqual(len(doc.lines), 1)
        line = doc.lines[0]
        self.assertEqual(line.atc, "WI100")
        self.assertEqual(flt(line.total), 15000)
        self.assertEqual(flt(line.tax_withheld), 750)
        self.assertEqual(flt(doc.total_tax), 750)
        self.assertEqual(doc.payee_name, "Santos, Maria, Cruz")
        self.assertEqual(doc.payee_tin, "555-666-777-00000")
        month_idx = (frappe.utils.getdate(today()).month - self.qs.month) + 1
        self.assertEqual(flt(line.get(f"month_{month_idx}")), 15000)

    def test_print_renders_the_form_face(self):
        make_purchase_invoice(self.sup, [(ensure_service_item(), 1, 10000, {})], submit=True)
        generate_quarter(TEST_COMPANY, str(self.qs))
        doc = frappe.get_doc("PH 2307 Issued", {"supplier": self.sup, "docstatus": 0})
        doc.submit()
        pf = frappe.get_doc("Print Format", "PH BIR 2307")
        html = frappe.render_template(pf.html, {"doc": doc, "frappe": frappe})
        for needle in ["Certificate of Creditable Tax Withheld at Source", "Part I", "Payee Information", "Part II", "Payor Information", "Part III", "WI100", "Santos, Maria, Cruz", "CONFORME", "Money Payments Subject to Withholding of Business Tax", "Data Privacy Act"]:
            self.assertIn(needle, html, needle)
        self.assertEqual(html.count('class="bx"'), 8 + 8 + 14 + 4 + 14 + 4 + 8 * 4)

    def test_reissue_only_after_cancel(self):
        make_purchase_invoice(self.sup, [(ensure_service_item(), 1, 10000, {})], submit=True)
        generate_quarter(TEST_COMPANY, str(self.qs))
        doc = frappe.get_doc("PH 2307 Issued", {"supplier": self.sup, "docstatus": 0})
        doc.submit()
        self.assertEqual(generate_quarter(TEST_COMPANY, str(self.qs)), [])
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({"doctype": "PH 2307 Issued", "company": TEST_COMPANY, "supplier": self.sup, "period_from": self.qs, "period_to": self.qe}).insert()
        doc.cancel()
        names = generate_quarter(TEST_COMPANY, str(self.qs))
        self.assertEqual(len(names), 1)

    def test_nothing_withheld_refuses(self):
        other = ensure_supplier_profile("_Test PH NonVAT Supplier", ph_ewt_category="None (no withholding)")
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({"doctype": "PH 2307 Issued", "company": TEST_COMPANY, "supplier": other, "period_from": self.qs, "period_to": self.qe}).insert()
