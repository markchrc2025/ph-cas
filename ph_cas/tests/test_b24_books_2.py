"""B24: Sales Journal, Purchase Journal, Inventory Book."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, get_first_day, get_last_day, today

from ph_cas.ph_cas.report.ph_inventory_book.ph_inventory_book import execute as inv
from ph_cas.ph_cas.report.ph_purchase_journal.ph_purchase_journal import execute as pj
from ph_cas.ph_cas.report.ph_sales_journal.ph_sales_journal import execute as sj
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import ensure_service_item, ensure_stock_item, ensure_supplier_profile, ensure_warehouse, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _item, _set_regime


class TestB24Books2(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")
        self.f = {"company": TEST_COMPANY, "from_date": get_first_day(today()), "to_date": get_last_day(today())}

    def tearDown(self):
        _set_regime("Non-VAT")

    def test_sales_journal_columns_and_tie(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {}), (_item("_PH Exempt", "VAT-exempt"), 1, 300, {})], submit=True)
        cols, rows = sj(self.f)
        row = [r for r in rows if r.get("name") == si.name][0]
        self.assertEqual(flt(row["ph_vatable_sales"]), 1000)
        self.assertEqual(flt(row["ph_exempt_sales"]), 300)
        self.assertEqual(flt(row["ph_vat_amount"]), 120)
        self.assertEqual(flt(row["grand_total"]), 1420)
        self.assertEqual(row["doc_type"], "Invoice")
        total = [r for r in rows if r.get("is_total_row")][0]
        self.assertEqual(flt(total["ph_vat_amount"]), flt(sum(flt(r.get("ph_vat_amount")) for r in rows if r.get("name")), 2))
        self.assertIn("TIES TO THE LEDGER", rows[-1]["customer_name"])

    def test_credit_note_appears_negative(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})], submit=True)
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

        cn = make_sales_return(si.name)
        cn.insert()
        cn.submit()
        cols, rows = sj(self.f)
        row = [r for r in rows if r.get("name") == cn.name][0]
        self.assertEqual(row["doc_type"], "Credit Note")
        self.assertLess(flt(row["grand_total"]), 0)

    def test_purchase_journal_columns_and_tie(self):
        sup = ensure_supplier_profile("_Test PH CPA Firm", ph_vat_status="VAT", ph_payee_type="Non-individual", ph_ewt_category="professional", ph_over_threshold=0)
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 20000, {})], submit=True)
        cols, rows = pj(self.f)
        row = [r for r in rows if r.get("name") == pi.name][0]
        self.assertEqual(flt(row["services"]), 20000)
        self.assertEqual(flt(row["input_vat"]), 2400)
        self.assertEqual(row["ph_ewt_atc"], "WC010")
        self.assertEqual(flt(row["ph_ewt_amount"]), 2000)
        self.assertIn("TIES TO THE LEDGER", rows[-1]["supplier_name"])

    def test_inventory_book(self):
        item = ensure_stock_item()
        wh = ensure_warehouse()
        se = frappe.get_doc({"doctype": "Stock Entry", "company": TEST_COMPANY, "stock_entry_type": "Material Receipt", "purpose": "Material Receipt", "posting_date": today(), "items": [{"item_code": item, "qty": 5, "t_warehouse": wh, "basic_rate": 10}]}).insert()
        se.submit()
        cols, rows = inv(self.f)
        row = [r for r in rows if r.get("item_code") == item and r.get("warehouse") == wh][0]
        self.assertGreaterEqual(flt(row["in_qty"]), 5)
        self.assertEqual(flt(row["closing_qty"]), flt(row["opening_qty"] + row["in_qty"] - row["out_qty"] + row["count_qty"]))
        self.assertEqual(flt(row["closing_value"]), flt(row["closing_qty"] * row["valuation_rate"], 2))
