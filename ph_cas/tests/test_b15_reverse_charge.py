"""B15: reverse-charge VAT on digital services and RBE purchases."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from ph_cas.setup.chart import account_for, setup_philippine_company
from ph_cas.tests.fixtures import ensure_service_item, ensure_supplier_profile, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _set_regime


class TestB15ReverseCharge(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")

    def tearDown(self):
        _set_regime("Non-VAT")

    def test_digital_service_subscription_vat_buyer(self):
        sup = ensure_supplier_profile("_Test PH Cloud Provider", ph_vat_status="Non-VAT", ph_is_nonresident_dsp=1, ph_ewt_category="None (no withholding)")
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 1000, {})], submit=True)
        self.assertEqual(pi.ph_rc_kind, "Digital services (non-resident)")
        self.assertEqual(pi.ph_rc_atc, "WV080")
        self.assertEqual(flt(pi.ph_rc_vat), 120)
        self.assertEqual(flt(pi.ph_rc_input_vat), 120)
        self.assertEqual(pi.ph_rc_claim_after_payment, 0)
        self.assertEqual(flt(pi.grand_total), 1000)  # the provider is paid the base
        self.assertEqual(flt(pi.ph_input_vat_services), 0)  # not ordinary input VAT
        credit = frappe.db.get_value("GL Entry", {"voucher_no": pi.name, "account": account_for(TEST_COMPANY, "wt_vat_payable"), "is_cancelled": 0}, "credit")
        debit = frappe.db.get_value("GL Entry", {"voucher_no": pi.name, "account": account_for(TEST_COMPANY, "input_vat_reverse_charge"), "is_cancelled": 0}, "debit")
        self.assertEqual(flt(credit), 120)
        self.assertEqual(flt(debit), 120)

    def test_digital_service_non_vat_buyer_books_cost(self):
        _set_regime("Non-VAT")
        sup = ensure_supplier_profile("_Test PH Cloud Provider", ph_is_nonresident_dsp=1)
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 1000, {})], submit=True)
        self.assertEqual(flt(pi.ph_rc_vat), 120)
        self.assertEqual(flt(pi.ph_rc_input_vat), 0)
        debit = frappe.db.get_value("GL Entry", {"voucher_no": pi.name, "account": account_for(TEST_COMPANY, "percentage_tax_expense"), "is_cancelled": 0}, "debit")
        self.assertEqual(flt(debit), 120)
        self.assertEqual(flt(pi.grand_total), 1000)

    def test_rbe_purchase_is_claimable_after_payment(self):
        sup = ensure_supplier_profile("_Test PH Ecozone Supplier", ph_vat_status="VAT", ph_is_rbe=1, ph_ewt_category="None (no withholding)")
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 5000, {})])
        self.assertEqual(pi.ph_rc_kind, "RBE purchase")
        self.assertEqual(pi.ph_rc_atc, "WV110")
        self.assertEqual(flt(pi.ph_rc_vat), 600)
        self.assertEqual(pi.ph_rc_claim_after_payment, 1)
        self.assertEqual(flt(pi.grand_total), 5000)
        self.assertEqual(flt(pi.ph_input_vat_services), 0)

    def test_ordinary_supplier_has_no_reverse_charge(self):
        sup = ensure_supplier_profile("_Test PH VAT Supplier", ph_vat_status="VAT", ph_is_rbe=0, ph_is_nonresident_dsp=0, ph_ewt_category="None (no withholding)")
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 1000, {})])
        self.assertFalse(pi.ph_rc_kind)
        self.assertEqual(flt(pi.ph_rc_vat), 0)

    def test_resave_keeps_one_pair_of_rows(self):
        sup = ensure_supplier_profile("_Test PH Cloud Provider", ph_is_nonresident_dsp=1)
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 1000, {})])
        pi.save()
        rows = [t for t in pi.taxes if "Reverse-charge" in (t.description or "")]
        self.assertEqual(len(rows), 2)
