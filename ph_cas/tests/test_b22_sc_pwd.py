"""B22: senior citizen and PWD discounts."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from ph_cas.setup.chart import account_for, setup_philippine_company
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _item, _set_regime
from ph_cas.tests.test_b20_prints import render


class TestB22SCPWD(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")

    def tearDown(self):
        _set_regime("Non-VAT")

    def test_restaurant_sale_to_a_senior(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 2, 250, {})], submit=True, ph_sc_pwd_applied=1, ph_sc_pwd_type="Senior Citizen", ph_sc_pwd_name="Lola Nena", ph_sc_pwd_id="OSCA-12345")
        self.assertEqual(flt(si.ph_sc_pwd_gross), 500)
        self.assertEqual(flt(si.ph_sc_pwd_discount), 100)
        self.assertEqual(si.ph_sc_pwd_rule, "SC-PWD-20")
        self.assertEqual(flt(si.ph_vat_amount), 0)
        self.assertEqual(flt(si.ph_exempt_sales), 500)
        self.assertEqual(flt(si.grand_total), 400)
        debit = frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": account_for(TEST_COMPANY, "sc_pwd_discount"), "is_cancelled": 0}, "debit")
        self.assertEqual(flt(debit), 100)
        html = render(si, "PH Sales Invoice")
        self.assertIn("Lola Nena", html)
        self.assertIn("OSCA-12345", html)
        self.assertIn("20% discount", html)
        self.assertIn("VAT-EXEMPT SALE", html)

    def test_holder_details_are_required(self):
        with self.assertRaises(frappe.ValidationError):
            _invoice([(_item("_PH VATable", "VATable"), 1, 100, {})], ph_sc_pwd_applied=1)

    def test_special_5_percent_discount_keeps_vat_and_is_capped(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})], ph_sc_pwd_special=1, ph_sc_pwd_type="PWD", ph_sc_pwd_name="Juan", ph_sc_pwd_id="PWD-1")
        self.assertEqual(flt(si.ph_sc_pwd_discount), 50)
        self.assertEqual(flt(si.ph_vat_amount), 120)
        self.assertEqual(flt(si.grand_total), 1070)
        with self.assertRaises(frappe.ValidationError):
            _invoice([(_item("_PH VATable", "VATable"), 1, 3000, {})], ph_sc_pwd_special=1, ph_sc_pwd_type="PWD", ph_sc_pwd_name="Juan", ph_sc_pwd_id="PWD-1")

    def test_report_lists_the_sale(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 300, {})], submit=True, ph_sc_pwd_applied=1, ph_sc_pwd_type="PWD", ph_sc_pwd_name="Ana", ph_sc_pwd_id="PWD-77")
        from ph_cas.ph_cas.report.ph_sc_pwd_sales.ph_sc_pwd_sales import execute

        cols, rows = execute({"company": TEST_COMPANY, "from_date": si.posting_date, "to_date": si.posting_date})
        row = [r for r in rows if r["name"] == si.name][0]
        self.assertEqual(flt(row["ph_sc_pwd_discount"]), 60)
        self.assertEqual(row["kind"], "20%")
