"""B20: invoice print formats and REPRINT."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.invoicing.printing import document_title, print_status
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import ensure_service_item, make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _item, _set_regime
from ph_cas.tests.test_b13_customer_withholding import _customer


def render(doc, fmt):
    """Render the format's Jinja with the document, the way printview does,
    without the bundled assets the test bench lacks. The template sees the safe
    Jinja globals only (no full `frappe` module): passing the module hid LDG-95."""
    doc.run_method("before_print", frappe._dict({"method": "print"}))
    pf = frappe.get_doc("Print Format", fmt)
    return frappe.render_template(pf.html, {"doc": doc})


class TestB20Prints(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")
        frappe.db.set_value("Company", TEST_COMPANY, {"tax_id": "123-456-789", "ph_accn": "ACCN-TEST-001", "ph_business_style": "Tala Trading"}, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)

    def tearDown(self):
        _set_regime("Non-VAT")

    def test_vat_invoice_carries_every_required_element(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 2, 500, {}), (_item("_PH Exempt", "VAT-exempt"), 1, 100, {})], submit=True)
        html = render(si, "PH Sales Invoice")
        for needle in ["SALES INVOICE", TEST_COMPANY, "Tala Trading", "VAT REG TIN 123-456-789-00000", si.bir_serial, "Sold to:", "VATable Sales", "VAT-Exempt Sales", "Zero-Rated Sales", "VAT Amount (12%)", "TOTAL AMOUNT DUE", "ACCN ACCN-TEST-001", "Series 00000001 to 99999999", "ORIGINAL COPY", "DUPLICATE COPY", "Printed by"]:
            self.assertIn(needle, html, needle)
        self.assertNotIn("REPRINT", html)

    def test_second_print_is_a_reprint_with_count_and_first_date(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})], submit=True)
        render(si, "PH Sales Invoice")
        self.assertEqual(print_status("Sales Invoice", si.name)["prints"], 1)
        html = render(si, "PH Sales Invoice")
        self.assertIn("REPRINT No. 2", html)
        self.assertIn("first printed", html)
        self.assertEqual(print_status("Sales Invoice", si.name)["prints"], 2)
        rec = frappe.get_all("PH Print Record", filters={"ref_name": si.name}, fields=["print_no", "copy_type"], order_by="print_no")
        self.assertEqual([(r.print_no, r.copy_type) for r in rec], [(1, "original"), (2, "reprint")])

    def test_print_records_are_insert_only(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})], submit=True)
        render(si, "PH Sales Invoice")
        name = frappe.db.get_value("PH Print Record", {"ref_name": si.name}, "name")
        with self.assertRaises(frappe.PermissionError):
            frappe.delete_doc("PH Print Record", name, force=True)

    def test_non_vat_invoice_shows_percentage_tax_base_and_exempt(self):
        _set_regime("Non-VAT")
        si = _invoice([(_item("_PH Exempt", "VAT-exempt"), 1, 100, {})], submit=True)
        html = render(si, "PH Sales Invoice")
        self.assertIn("NON-VAT REG TIN", html)
        self.assertIn("EXEMPT", html)
        self.assertNotIn("VAT Amount", html)

    def test_credit_note_title_and_reference(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})], submit=True)
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

        cn = make_sales_return(si.name)
        cn.insert()
        cn.submit()
        self.assertEqual(document_title(cn), "CREDIT NOTE")
        html = render(cn, "PH Sales Invoice")
        self.assertIn("CREDIT NOTE", html)
        self.assertIn(si.bir_serial, html)

    def test_less_withholding_line_prints_for_withholding_customers(self):
        twa = _customer("_Test PH TWA Corp", ph_top_withholding_agent=1)
        si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=twa, submit=True)
        html = render(si, "PH Sales Invoice")
        self.assertIn("Less: Withholding Tax (WC160)", html)
        self.assertIn("AMOUNT DUE NET OF WITHHOLDING", html)

    def test_collection_receipt(self):
        si = _invoice([(_item("_PH VATable", "VATable"), 1, 1000, {})], submit=True)
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        pe = get_payment_entry("Sales Invoice", si.name)
        pe.reference_no = "CR-1"
        pe.reference_date = frappe.utils.today()
        pe.insert()
        pe.submit()
        self.assertTrue(pe.bir_serial)
        html = render(pe, "PH Collection Receipt")
        self.assertIn("COLLECTION RECEIPT", html)
        self.assertIn("THIS DOCUMENT IS NOT VALID FOR CLAIM OF INPUT TAX", html)
        self.assertIn(si.bir_serial, html)
        self.assertIn(pe.bir_serial, html)

    def test_formats_call_helpers_through_ph_attr_only(self):
        """LDG-95: Frappe v16's safe Jinja has no frappe.get_attr; ph_attr resolves
        the allowlisted print helpers and nothing else."""
        import os
        import re

        from ph_cas.invoicing.printing import PRINT_HELPERS, ph_attr

        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ph_cas", "print_format")
        used = set()
        for d in os.listdir(root):
            html = os.path.join(root, d, f"{d}.html")
            if os.path.exists(html):
                text = open(html, encoding="utf-8").read()
                self.assertNotIn("get_attr(", text, d)
                used |= set(re.findall(r"ph_attr\(['\"]([^'\"]+)['\"]\)", text))
        self.assertTrue(used)
        self.assertLessEqual(used, PRINT_HELPERS)
        self.assertTrue(callable(ph_attr("ph_cas.invoicing.printing.buyer_facts")))
        with self.assertRaises(frappe.ValidationError):
            ph_attr("frappe.db.sql")

    def test_default_print_formats_are_set(self):
        self.assertEqual(frappe.get_meta("Sales Invoice").default_print_format, "PH Sales Invoice")
        self.assertEqual(frappe.get_meta("Payment Entry").default_print_format, "PH Collection Receipt")
