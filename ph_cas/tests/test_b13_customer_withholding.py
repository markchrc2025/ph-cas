"""B13: withholding by customers and 2307s received."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from ph_cas.setup.chart import account_for, setup_philippine_company
from ph_cas.tax.customer_withholding import shows_less_withholding_line
from ph_cas.tests.fixtures import ensure_customer, ensure_service_item, ensure_stock_item
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _set_regime


def _customer(name, **flags):
    c = ensure_customer(name)
    for k, v in flags.items():
        frappe.db.set_value("Customer", c, k, v)
    frappe.clear_document_cache("Customer", c)
    return c


def _pay(si, amount):
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

    pe = get_payment_entry("Sales Invoice", si.name)
    pe.paid_amount = amount
    pe.received_amount = amount
    pe.references[0].allocated_amount = amount
    pe.insert()
    pe.submit()
    return pe


class TestB13CustomerWithholding(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")
        frappe.db.set_value("Company", TEST_COMPANY, "ph_taxpayer_type", "Non-individual", update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)

    def tearDown(self):
        _set_regime("Non-VAT")

    def test_ordinary_customer_has_no_withholding(self):
        si = _invoice([(ensure_service_item(), 1, 1000, {})])
        self.assertFalse(si.ph_wht_applicable)
        self.assertEqual(flt(si.ph_net_due), flt(si.grand_total))

    def test_top_withholding_agent_withholds_on_services_and_goods(self):
        twa = _customer("_Test PH TWA Corp", ph_top_withholding_agent=1)
        si = _invoice([(ensure_service_item(), 1, 1000, {}), (ensure_stock_item(), 10, 100, {"ph_vat_class": "VATable"})], customer=twa)
        self.assertTrue(si.ph_wht_applicable)
        self.assertEqual(set(si.ph_wht_atc.split(",")), {"WC160", "WC158"})
        self.assertEqual(flt(si.ph_wht_base), 2000)
        self.assertEqual(flt(si.ph_wht_amount), 30)  # 2% of 1000 + 1% of 1000
        self.assertEqual(flt(si.grand_total), 2240)
        self.assertEqual(flt(si.ph_net_due), 2210)
        self.assertIn("EWT-WC160", si.ph_wht_rules)

    def test_individual_seller_gets_wi_codes(self):
        frappe.db.set_value("Company", TEST_COMPANY, "ph_taxpayer_type", "Individual", update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        try:
            twa = _customer("_Test PH TWA Corp", ph_top_withholding_agent=1)
            si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=twa)
            self.assertEqual(si.ph_wht_atc, "WI160")
        finally:
            frappe.db.set_value("Company", TEST_COMPANY, "ph_taxpayer_type", "Non-individual", update_modified=False)
            frappe.clear_document_cache("Company", TEST_COMPANY)

    def test_government_customer_withholds_income_tax_and_vat(self):
        gov = _customer("_Test PH Gov Agency", ph_is_government=1)
        si = _invoice([(ensure_service_item(), 1, 1000, {"ph_vat_class": "Government"})], customer=gov)
        self.assertEqual(si.ph_wht_atc, "WI650")
        self.assertEqual(flt(si.ph_wht_amount), 20)
        self.assertEqual(si.ph_wvat_atc, "WV020")
        self.assertEqual(flt(si.ph_wvat_amount), 50)
        self.assertEqual(flt(si.ph_wht_total), 70)
        self.assertEqual(flt(si.grand_total), 1120)
        self.assertEqual(flt(si.ph_net_due), 1050)

    def test_government_customer_of_non_vat_seller_withholds_percentage_tax(self):
        _set_regime("Non-VAT")
        gov = _customer("_Test PH Gov Agency", ph_is_government=1)
        si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=gov)
        self.assertEqual(si.ph_wpt_atc, "WB080")
        self.assertEqual(flt(si.ph_wpt_amount), 30)
        self.assertEqual(flt(si.ph_wht_amount), 20)
        self.assertEqual(flt(si.ph_net_due), 950)

    def test_withholding_on_request_needs_atc_and_rate(self):
        plain = ensure_customer()
        with self.assertRaises(frappe.ValidationError):
            _invoice([(ensure_service_item(), 1, 1000, {})], customer=plain, ph_wht_applicable=1)
        si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=plain, ph_wht_applicable=1, ph_wht_atc="WC010", ph_wht_rate=10)
        self.assertEqual(flt(si.ph_wht_amount), 100)
        self.assertEqual(flt(si.ph_net_due), 1020)

    def test_less_withholding_line_rule_date(self):
        si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=_customer("_Test PH TWA Corp", ph_top_withholding_agent=1))
        self.assertTrue(shows_less_withholding_line(si))  # today is after 16 Oct 2026

    def test_net_payment_books_the_withheld_tax_and_closes_the_invoice(self):
        twa = _customer("_Test PH TWA Corp", ph_top_withholding_agent=1)
        si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=twa, submit=True)
        self.assertEqual(flt(si.ph_wht_amount), 20)
        pe = _pay(si, 1100)
        self.assertEqual(flt(pe.ph_wht_deducted), 20)
        self.assertEqual(len([d for d in pe.deductions if d.description.startswith("Withheld by customer")]), 1)
        self.assertEqual(pe.deductions[0].account, account_for(TEST_COMPANY, "cwt_receivable"))
        self.assertEqual(flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount")), 0)
        gle = frappe.db.get_value("GL Entry", {"voucher_no": pe.name, "account": account_for(TEST_COMPANY, "cwt_receivable"), "is_cancelled": 0}, "debit")
        self.assertEqual(flt(gle), 20)

    def test_full_payment_books_no_deduction(self):
        twa = _customer("_Test PH TWA Corp", ph_top_withholding_agent=1)
        si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=twa, submit=True)
        pe = _pay(si, 1120)
        self.assertEqual(flt(pe.ph_wht_deducted), 0)

    def test_2307_received_and_reconciliation(self):
        twa = _customer("_Test PH TWA Corp", ph_top_withholding_agent=1)
        si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=twa, submit=True)
        _pay(si, 1100)
        from frappe.utils import get_first_day, get_last_day

        doc = frappe.get_doc(
            {
                "doctype": "PH 2307 Received",
                "company": TEST_COMPANY,
                "customer": twa,
                "period_from": get_first_day(today()),
                "period_to": get_last_day(today()),
                "lines": [{"atc": "WC160", "kind": "Income tax", "month_1": 1000, "tax_withheld": 20}],
            }
        ).insert()
        doc.submit()
        self.assertEqual(flt(doc.total_tax), 20)
        self.assertRegex(doc.quarter, r"^\d{4}-Q[1-4]$")
        from ph_cas.ph_cas.report.ph_2307_received_reconciliation.ph_2307_received_reconciliation import execute

        cols, rows = execute({"company": TEST_COMPANY, "from_date": get_first_day(today()), "to_date": get_last_day(today())})
        row = [r for r in rows if r["customer"] == twa][0]
        self.assertGreaterEqual(row["withheld"], 20)
        self.assertGreaterEqual(row["certified"], 20)
