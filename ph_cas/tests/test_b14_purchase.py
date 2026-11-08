"""B14: purchase side input VAT and expanded withholding."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from ph_cas.setup.chart import account_for, setup_philippine_company
from ph_cas.tests.fixtures import ensure_service_item, ensure_stock_item, ensure_supplier_profile, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _set_regime


def _capital_item(code="_Test PH Capital Item"):
    if not frappe.db.exists("Item", code):
        frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": code, "item_group": "Products", "stock_uom": "Nos", "is_stock_item": 0, "ph_is_capital_good": 1, "ph_vat_class": "VATable"}).insert(ignore_permissions=True)
    return code


def _twa(flag):
    frappe.db.set_value("Company", TEST_COMPANY, "ph_top_withholding_agent", flag, update_modified=False)
    frappe.clear_document_cache("Company", TEST_COMPANY)


class TestB14Purchase(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")
        _twa(0)

    def tearDown(self):
        _set_regime("Non-VAT")
        _twa(0)

    def test_input_vat_by_kind_from_a_vat_supplier(self):
        sup = ensure_supplier_profile("_Test PH VAT Supplier", ph_vat_status="VAT", ph_ewt_category="None (no withholding)")
        pi = make_purchase_invoice(sup, [(ensure_stock_item(), 10, 100, {}), (ensure_service_item(), 1, 500, {}), (_capital_item(), 1, 2000, {})])
        self.assertEqual(flt(pi.ph_input_vat_goods), 120)
        self.assertEqual(flt(pi.ph_input_vat_services), 60)
        self.assertEqual(flt(pi.ph_input_vat_capital), 240)
        self.assertEqual(flt(pi.grand_total), 3500 + 420)
        accounts = {t.account_head for t in pi.taxes}
        self.assertIn(account_for(TEST_COMPANY, "input_vat_goods"), accounts)
        self.assertIn(account_for(TEST_COMPANY, "input_vat_capital"), accounts)
        self.assertIn("VAT-IN-CAPITAL-FULL", pi.ph_ewt_rule)

    def test_non_vat_supplier_gives_no_input_vat(self):
        sup = ensure_supplier_profile("_Test PH NonVAT Supplier", ph_vat_status="Non-VAT", ph_ewt_category="None (no withholding)")
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 500, {})])
        self.assertEqual(flt(pi.ph_input_vat_services), 0)
        self.assertEqual(flt(pi.ph_exempt_purchases), 500)
        self.assertEqual(flt(pi.grand_total), 500)

    def test_non_vat_buyer_treats_vat_as_cost(self):
        _set_regime("Non-VAT")
        sup = ensure_supplier_profile("_Test PH VAT Supplier", ph_vat_status="VAT", ph_ewt_category="None (no withholding)")
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 500, {})])
        self.assertEqual(flt(pi.ph_vat_cost), 60)
        self.assertEqual(flt(pi.ph_input_vat_services), 0)
        self.assertEqual(flt(pi.grand_total), 560)

    def test_rent_from_an_individual_withholds_5_percent(self):
        sup = ensure_supplier_profile("_Test PH Lessor", ph_vat_status="Non-VAT", ph_payee_type="Individual", ph_last_name="Reyes", ph_first_name="Ana", ph_ewt_category="rent")
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 10000, {})])
        self.assertEqual(pi.ph_ewt_atc, "WI100")
        self.assertEqual(flt(pi.ph_ewt_rate), 5)
        self.assertEqual(flt(pi.ph_ewt_base), 10000)
        self.assertEqual(flt(pi.ph_ewt_amount), 500)
        self.assertEqual(flt(pi.grand_total), 9500)
        self.assertEqual(pi.ph_ewt_period, today()[:7])

    def test_professional_fees_rates_by_threshold_and_vat_supplier_base(self):
        sup = ensure_supplier_profile("_Test PH CPA Firm", ph_vat_status="VAT", ph_payee_type="Non-individual", ph_ewt_category="professional", ph_over_threshold=0)
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 20000, {})])
        self.assertEqual(pi.ph_ewt_atc, "WC010")
        self.assertEqual(flt(pi.ph_ewt_amount), 2000)  # 10% of the VAT-exclusive 20,000
        self.assertEqual(flt(pi.ph_input_vat_services), 2400)
        self.assertEqual(flt(pi.grand_total), 20000 + 2400 - 2000)
        sup = ensure_supplier_profile("_Test PH CPA Firm", ph_over_threshold=1)
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 20000, {})])
        self.assertEqual(pi.ph_ewt_atc, "WC011")
        self.assertEqual(flt(pi.ph_ewt_amount), 3000)

    def test_ewt_posts_to_the_payable_on_submit(self):
        sup = ensure_supplier_profile("_Test PH Contractor", ph_vat_status="Non-VAT", ph_payee_type="Non-individual", ph_ewt_category="contractor")
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 5000, {})], submit=True)
        self.assertEqual(pi.ph_ewt_atc, "WC120")
        credit = frappe.db.get_value("GL Entry", {"voucher_no": pi.name, "account": account_for(TEST_COMPANY, "ewt_payable"), "is_cancelled": 0}, "credit")
        self.assertEqual(flt(credit), 100)
        self.assertEqual(flt(frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount")), 4900)

    def test_goods_and_services_categories_apply_only_to_top_withholding_agents(self):
        sup = ensure_supplier_profile("_Test PH Goods Supplier", ph_vat_status="Non-VAT", ph_payee_type="Non-individual", ph_ewt_category="goods")
        pi = make_purchase_invoice(sup, [(ensure_stock_item(), 10, 100, {})])
        self.assertFalse(pi.ph_ewt_atc)
        _twa(1)
        pi = make_purchase_invoice(sup, [(ensure_stock_item(), 10, 100, {})])
        self.assertEqual(pi.ph_ewt_atc, "WC158")
        self.assertEqual(flt(pi.ph_ewt_amount), 10)

    def test_no_withholding_needs_a_reason(self):
        sup = ensure_supplier_profile("_Test PH Contractor", ph_ewt_category="contractor")
        with self.assertRaises(frappe.ValidationError):
            make_purchase_invoice(sup, [(ensure_service_item(), 1, 5000, {})], ph_no_withholding=1)
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 5000, {})], ph_no_withholding=1, ph_no_withholding_reason="Withheld on the advance paid in October")
        self.assertEqual(flt(pi.ph_ewt_amount), 0)
        self.assertEqual(flt(pi.grand_total), 5000)

    def test_advance_payment_withholds_at_payment(self):
        sup = ensure_supplier_profile("_Test PH Contractor", ph_vat_status="Non-VAT", ph_ewt_category="contractor")
        pe = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "payment_type": "Pay",
                "company": TEST_COMPANY,
                "party_type": "Supplier",
                "party": sup,
                "posting_date": today(),
                "paid_from": frappe.db.get_value("Account", {"company": TEST_COMPANY, "account_name": "Cash"}, "name"),
                "paid_to": frappe.db.get_value("Account", {"company": TEST_COMPANY, "account_name": "Creditors"}, "name"),
                "paid_amount": 4900,
                "received_amount": 4900,
                "reference_no": "ADV-1",
                "reference_date": today(),
            }
        ).insert()
        self.assertEqual(flt(pe.ph_ewt_on_advance), 98)
        self.assertEqual(pe.ph_ewt_advance_atc, "WC120")
        self.assertTrue([d for d in pe.deductions if d.description.startswith("EWT on advance")])
