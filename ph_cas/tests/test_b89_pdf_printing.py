"""B89: PDFs are made with wkhtmltopdf and Print prints the server's PDF."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.invoicing.setup import force_pdf_printing


class TestB89PdfPrinting(IntegrationTestCase):
    def test_settings_and_formats_use_wkhtmltopdf(self):
        frappe.db.set_single_value("Print Settings", {"pdf_generator": "chrome", "print_generated_pdf": 0})
        force_pdf_printing()
        s = frappe.get_single("Print Settings")
        self.assertEqual(s.pdf_generator, "wkhtmltopdf")
        self.assertEqual(int(s.print_generated_pdf), 1)
        self.assertFalse(frappe.get_all("Print Format", filters={"pdf_generator": "chrome"}, pluck="name"))
        if frappe.db.exists("Print Format", "PH Sales Invoice"):
            self.assertEqual(frappe.db.get_value("Print Format", "PH Sales Invoice", "pdf_generator"), "wkhtmltopdf")
