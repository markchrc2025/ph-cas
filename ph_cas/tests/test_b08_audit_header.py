"""B08: audit trail report and the Annex B header."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime

from ph_cas.audit.export import csv_with_header, xlsx_with_header
from ph_cas.audit.header import ph_header, ph_header_lines, software_name
from ph_cas.tests.fixtures import make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY


class TestB08AuditHeader(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_header_lines_carry_every_annex_b_fact(self):
        frappe.db.set_value("Company", TEST_COMPANY, "tax_id", "000-000-000", update_modified=False)
        frappe.clear_cache(doctype="Company")
        lines = ph_header_lines(TEST_COMPANY)
        text = "\n".join(lines)
        self.assertIn(TEST_COMPANY, text)
        self.assertIn("REG TIN 000-000-000-00000", text)
        self.assertIn(f"Software: {software_name()} version", text)
        self.assertNotIn("ERPNext", text)
        self.assertNotIn("Frappe", text)
        self.assertIn("Printed by: Administrator", text)
        self.assertIn("Printed on: ", text)
        self.assertEqual(len(lines), 6)

    def test_header_html_escapes_and_renders(self):
        html = ph_header({"company": TEST_COMPANY})
        self.assertIn('class="ph-bir-header"', html)
        self.assertIn("Printed by", html)

    def test_letter_head_exists_is_default_and_renders_through_jinja(self):
        lh = frappe.get_doc("Letter Head", "BIR Header")
        self.assertEqual(lh.is_default, 1)
        rendered = frappe.render_template(lh.content, {"doc": {"company": TEST_COMPANY}})
        self.assertIn("Printed on", rendered)

    def test_product_name_setting_feeds_the_header(self):
        s = frappe.get_doc("PH CAS Settings")
        before = s.product_name
        s.product_name = "Tala Books"
        s.save()
        try:
            self.assertEqual(software_name(), "Tala Books")
            self.assertIn("Software: Tala Books", "\n".join(ph_header_lines(TEST_COMPANY)))
        finally:
            s.product_name = before
            s.save()

    def test_csv_and_xlsx_exports_start_with_the_header(self):
        data = csv_with_header(["a", "b"], [[1, 2]], TEST_COMPANY).decode("utf-8-sig")
        lines = data.split("\r\n")
        self.assertIn(f"Software: {software_name()}", lines[3])
        self.assertEqual(lines[7], "a,b")
        self.assertEqual(lines[8], "1,2")
        xlsx = xlsx_with_header(["a", "b"], [[1, 2]], TEST_COMPANY)
        self.assertEqual(xlsx[:2], b"PK")

    def test_audit_trail_report_merges_sources_in_time_order(self):
        from ph_cas.ph_cas.report.bir_audit_trail.bir_audit_trail import execute

        si = make_sales_invoice()
        si.reload()
        si.po_no = "PO-AUDIT-1"
        si.save()
        # Frappe's test environment does not write Version rows, so one is
        # inserted the way Frappe writes them, to prove the merge.
        v = frappe.new_doc("Version")
        v.ref_doctype = "Sales Invoice"
        v.docname = si.name
        v.data = frappe.as_json({"changed": [["po_no", "", "PO-AUDIT-1"]]})
        v.insert(ignore_permissions=True)
        filters = {"from_date": add_days(now_datetime(), -1), "to_date": add_days(now_datetime(), 1), "ref_name": si.name}
        columns, rows = execute(filters)
        sources = {r["source"] for r in rows}
        self.assertIn("Event Log", sources)
        self.assertIn("Version", sources)
        self.assertIn("po_no:  -> PO-AUDIT-1", [r["details"] for r in rows if r["source"] == "Version"])
        events = [r["event"] for r in rows if r["source"] == "Event Log"]
        self.assertIn("submit", events)
        stamps = [str(r["timestamp"]) for r in rows]
        self.assertEqual(stamps, sorted(stamps))

    def test_chain_check_report_says_intact(self):
        from ph_cas.ph_cas.report.ph_chain_check.ph_chain_check import execute

        columns, rows = execute({})
        self.assertEqual(rows[0]["value"], "YES")
