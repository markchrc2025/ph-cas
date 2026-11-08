"""B12: sales side VAT classes, output VAT, percentage-tax base."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from ph_cas.setup.chart import account_for, setup_philippine_company
from ph_cas.tax.vat import OUTPUT_VAT_DESCRIPTION, threshold_status
from ph_cas.tests.fixtures import acc, ensure_customer
from ph_cas.tests.setup import TEST_COMPANY


def _item(code, cls):
    if not frappe.db.exists("Item", code):
        frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": code, "item_group": "Services", "stock_uom": "Nos", "is_stock_item": 0, "ph_vat_class": cls}).insert(ignore_permissions=True)
    else:
        frappe.db.set_value("Item", code, "ph_vat_class", cls)
        frappe.clear_document_cache("Item", code)
    return code


def _invoice(lines, customer=None, submit=False, **kw):
    si = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "company": TEST_COMPANY,
            "customer": customer or ensure_customer(),
            "posting_date": today(),
            "due_date": today(),
            "debit_to": acc("Debtors"),
            "items": [{"item_code": code, "qty": qty, "rate": rate, "income_account": acc("Sales"), "cost_center": acc("Main"), **extra} for code, qty, rate, extra in lines],
            **kw,
        }
    ).insert()
    if submit:
        si.submit()
    return si


def _set_regime(status):
    frappe.db.set_value("Company", TEST_COMPANY, "ph_vat_status", status, update_modified=False)
    frappe.clear_document_cache("Company", TEST_COMPANY)
    frappe.clear_cache(doctype="Company")


class TestB12SalesVAT(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")

    def tearDown(self):
        _set_regime("Non-VAT")

    def test_mixed_invoice_buckets_and_output_vat(self):
        si = _invoice(
            [
                (_item("_PH VATable", "VATable"), 1, 1000, {}),
                (_item("_PH Exempt", "VAT-exempt"), 1, 300, {}),
                (_item("_PH Zero", "Zero-rated"), 1, 500, {}),
            ]
        )
        self.assertEqual(si.ph_tax_regime, "VAT")
        self.assertEqual(flt(si.ph_vatable_sales), 1000)
        self.assertEqual(flt(si.ph_exempt_sales), 300)
        self.assertEqual(flt(si.ph_zero_rated_sales), 500)
        self.assertEqual(flt(si.ph_vat_amount), 120)
        self.assertEqual(flt(si.ph_vat_rate), 12)
        self.assertEqual(si.ph_vat_rule, "VAT-OUT-12")
        vat_rows = [t for t in si.taxes if t.description == OUTPUT_VAT_DESCRIPTION]
        self.assertEqual(len(vat_rows), 1)
        self.assertEqual(vat_rows[0].account_head, account_for(TEST_COMPANY, "output_vat"))
        self.assertEqual(flt(si.grand_total), 1920)
        self.assertEqual(flt(si.ph_pt_base), 0)

    def test_output_vat_posts_to_the_mapped_account_on_submit(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 2, 500, {})], submit=True)
        gle = frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": account_for(TEST_COMPANY, "output_vat"), "is_cancelled": 0}, "credit")
        self.assertEqual(flt(gle), 120)

    def test_line_class_override_wins_over_the_item(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {"ph_vat_class": "VAT-exempt"})])
        self.assertEqual(flt(si.ph_vat_amount), 0)
        self.assertEqual(flt(si.ph_exempt_sales), 1000)
        self.assertFalse([t for t in si.taxes if t.description == OUTPUT_VAT_DESCRIPTION])

    def test_government_sale_carries_full_output_vat(self):
        gov = ensure_customer("_Test PH Government Agency")
        frappe.db.set_value("Customer", gov, "ph_is_government", 1)
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {"ph_vat_class": "Government"})], customer=gov)
        self.assertEqual(flt(si.ph_government_sales), 1000)
        self.assertEqual(flt(si.ph_vatable_sales), 1000)
        self.assertEqual(flt(si.ph_vat_amount), 120)

    def test_resave_does_not_duplicate_the_vat_row(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})])
        si.save()
        si.save()
        self.assertEqual(len([t for t in si.taxes if t.description == OUTPUT_VAT_DESCRIPTION]), 1)
        self.assertEqual(flt(si.grand_total), 1120)

    def test_non_vat_company_gets_no_vat_and_a_percentage_tax_base(self):
        _set_regime("Non-VAT")
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {}), (_item("_PH Exempt", "VAT-exempt"), 1, 200, {})])
        self.assertEqual(si.ph_tax_regime, "Non-VAT")
        self.assertEqual(flt(si.ph_vat_amount), 0)
        self.assertEqual(flt(si.grand_total), 1200)
        self.assertEqual(flt(si.ph_pt_base), 1000)
        self.assertEqual(flt(si.ph_exempt_sales), 200)
        self.assertFalse([t for t in si.taxes if t.description == OUTPUT_VAT_DESCRIPTION])

    def test_non_vat_company_cannot_issue_zero_rated_lines(self):
        _set_regime("Non-VAT")
        with self.assertRaises(frappe.ValidationError):
            _invoice([(_item("_PH Zero", "Zero-rated"), 1, 500, {})])

    def test_threshold_watch(self):
        s = threshold_status(TEST_COMPANY)
        self.assertEqual(s["threshold"], 3000000)
        self.assertEqual(s["rule"], "VAT-THRESHOLD-3M")
        self.assertIn("exceeded", s)
        from ph_cas.ph_cas.report.ph_vat_threshold_watch.ph_vat_threshold_watch import execute

        cols, rows = execute({})
        self.assertTrue(any(r["company"] == TEST_COMPANY for r in rows))
