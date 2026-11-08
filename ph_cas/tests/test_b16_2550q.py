"""B16: 2550Q figures."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.returns import get_or_create, quarter_bounds
from ph_cas.tests.fixtures import ensure_service_item, ensure_stock_item, ensure_supplier_profile, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _item, _set_regime


class TestB16_2550Q(IntegrationTestCase):
    """The quarter already holds documents from earlier tests, so each check
    compares the figures before and after known documents are added."""

    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")
        self.start, self.end = quarter_bounds(today())

    def tearDown(self):
        _set_regime("Non-VAT")

    def figures(self):
        doc = get_or_create(TEST_COMPANY, "2550Q", self.start, self.end)
        return doc, {r.item: flt(r.amount) for r in doc.lines}

    def test_sales_side_items(self):
        doc0, f0 = self.figures()
        _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {}), (_item("_PH Exempt", "VAT-exempt"), 1, 300, {}), (_item("_PH Zero", "Zero-rated"), 1, 500, {})], submit=True)
        doc, f = self.figures()
        self.assertEqual(f["31A"] - f0["31A"], 1000)
        self.assertEqual(f["31B"] - f0["31B"], 120)
        self.assertEqual(f["32A"] - f0["32A"], 500)
        self.assertEqual(f["33A"] - f0["33A"], 300)
        self.assertEqual(f["34A"] - f0["34A"], 1800)
        self.assertEqual(doc.name, f"2550Q-{doc.period_label}-TPC")
        self.assertRegex(doc.period_label, r"^\d{4}-Q[1-4]$")

    def test_purchase_side_items_and_net(self):
        sup = ensure_supplier_profile("_Test PH VAT Supplier", ph_vat_status="VAT", ph_ewt_category="None (no withholding)", ph_is_rbe=0, ph_is_nonresident_dsp=0)
        doc0, f0 = self.figures()
        make_purchase_invoice(sup, [(ensure_stock_item(), 10, 100, {}), (ensure_service_item(), 1, 500, {})], submit=True)
        nonvat = ensure_supplier_profile("_Test PH NonVAT Supplier", ph_vat_status="Non-VAT", ph_ewt_category="None (no withholding)")
        make_purchase_invoice(nonvat, [(ensure_service_item(), 1, 200, {})], submit=True)
        doc, f = self.figures()
        self.assertEqual(f["44A"] - f0["44A"], 1500)
        self.assertEqual(f["44B"] - f0["44B"], 180)
        self.assertEqual(f["48A"] - f0["48A"], 200)
        self.assertEqual(f["50B"] - f0["50B"], 180)
        self.assertEqual(f["61"], flt(f["37B"] - f["60B"], 2))
        self.assertEqual(f["21"], flt(f["15"] - f["20"], 2))

    def test_digital_services_go_to_item_45(self):
        dsp = ensure_supplier_profile("_Test PH Cloud Provider", ph_is_nonresident_dsp=1, ph_vat_status="Non-VAT")
        doc0, f0 = self.figures()
        make_purchase_invoice(dsp, [(ensure_service_item(), 1, 1000, {})], submit=True)
        doc, f = self.figures()
        self.assertEqual(f["45A"] - f0["45A"], 1000)
        self.assertEqual(f["45B"] - f0["45B"], 120)
        self.assertEqual(f["44B"], f0["44B"])

    def test_rbe_input_vat_counts_only_when_paid(self):
        rbe = ensure_supplier_profile("_Test PH Ecozone Supplier", ph_vat_status="VAT", ph_is_rbe=1, ph_ewt_category="None (no withholding)")
        doc0, f0 = self.figures()
        pi = make_purchase_invoice(rbe, [(ensure_service_item(), 1, 5000, {})], submit=True)
        doc, f = self.figures()
        self.assertEqual(f["44B"], f0["44B"])
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        pe = get_payment_entry("Purchase Invoice", pi.name)
        pe.reference_no = "RBE-1"
        pe.reference_date = today()
        pe.insert()
        pe.submit()
        doc, f = self.figures()
        self.assertEqual(f["44B"] - f0["44B"], 600)

    def test_exempt_sales_ratable_input_tax(self):
        doc, f = self.figures()
        if f["34A"] and f["33A"]:
            self.assertEqual(f["53B"], flt(f["50B"] * f["33A"] / f["34A"], 2))

    def test_creditable_vat_withheld_from_2307s(self):
        from frappe.utils import get_first_day, get_last_day

        from ph_cas.tests.fixtures import ensure_customer

        gov = ensure_customer("_Test PH Gov Agency")
        doc0, f0 = self.figures()
        rec = frappe.get_doc({"doctype": "PH 2307 Received", "company": TEST_COMPANY, "customer": gov, "period_from": get_first_day(today()), "period_to": get_last_day(today()), "lines": [{"atc": "WV020", "kind": "VAT", "month_1": 1000, "tax_withheld": 50}]}).insert()
        rec.submit()
        doc, f = self.figures()
        self.assertEqual(f["16"] - f0["16"], 50)
        self.assertEqual(f["21"], flt(f["15"] - f["20"], 2))

    def test_typed_adjustment_needs_a_reason_and_filed_figures_freeze(self):
        doc, f = self.figures()
        doc.append("adjustments", {"item": "42B", "label": "Others", "amount": 10})
        with self.assertRaises(frappe.ValidationError):
            doc.save()
        doc.reload()
        doc.append("adjustments", {"item": "42B", "label": "Others", "amount": 10, "reason": "Transitional input tax per CPA"})
        doc.save()
        self.assertEqual(doc.figure("42B"), 10)
        doc.filed = 1
        doc.filed_reference = "eBIRForms 2550Q confirmation"
        doc.save()
        doc.lines[0].amount = flt(doc.lines[0].amount) + 1
        with self.assertRaises(frappe.ValidationError):
            doc.save()
        doc.reload()
        with self.assertRaises(frappe.ValidationError):
            doc.recompute()
        doc.db_set("filed", 0)

    def test_output_vat_credit_claim_rules(self):
        from ph_cas.tax.ovc import claim_output_vat_credit

        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})], submit=True, ph_credit_term_days=30)
        with self.assertRaises(frappe.ValidationError):
            claim_output_vat_credit(si.name, str(self.start))  # the term has not lapsed in a past quarter
        from frappe.utils import add_days, add_months

        lapse_start, lapse_end = quarter_bounds(add_days(today(), 30))
        quarter = claim_output_vat_credit(si.name, str(add_days(lapse_end, 1)))
        self.assertRegex(quarter, r"^\d{4}-Q[1-4]$")
        self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, "ph_ovc_claimed"), 1)
