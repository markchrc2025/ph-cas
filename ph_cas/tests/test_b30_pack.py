"""B30: the registration pack."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.registration.pack import build, conformance_rows
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY


class TestB30Pack(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        s = frappe.get_single("PH CAS Settings")
        s.provider_name = "MCRC Tax and Accounting Services"
        s.provider_signatory = "Christian R. Canlubo"
        s.provider_signatory_position = "Proprietor"
        s.save()
        make_sales_invoice()

    def test_conformance_rows_parse(self):
        rows = conformance_rows()
        self.assertGreaterEqual(len(rows), 19)
        self.assertTrue(all(r["answer"] in ("YES", "NO") for r in rows))
        item6 = [r for r in rows if r["item"] == "6"][0]
        self.assertEqual(item6["answer"], "NO")  # e-invoicing not bundled

    def test_pack_contents(self):
        out = build(TEST_COMPANY)
        names = set(out["files"])
        for n in ("00_MANIFEST.json", "01_Annex_C1_System_Description.txt", "02_Annex_B_Answers.txt", "03_Joint_Sworn_Statement.txt", "04_Conformance_Report.txt", "05_Sample_Sales_Invoice.html", "16_Audit_Trail_30_days.html", "17_Chain_Check.html"):
            self.assertIn(n, names)
        self.assertTrue([n for n in names if "Book_General_Journal" in n])
        sworn = out["files"]["03_Joint_Sworn_Statement.txt"].decode()
        self.assertIn("Christian R. Canlubo", sworn)
        self.assertIn("MCRC Tax and Accounting Services", sworn)
        self.assertIn("no facility that may suppress", sworn)
        answers = out["files"]["02_Annex_B_Answers.txt"].decode()
        self.assertIn("Item 6: NO", answers)
        self.assertIn("Item 1: YES", answers)
        self.assertIn("6", out["manifest"]["annex_b_gaps"])
        c1 = out["files"]["01_Annex_C1_System_Description.txt"].decode()
        self.assertIn("ANNEX C-1", c1)
        self.assertIn("PH CAS version", c1)

    def test_specimen_render_does_not_count_as_a_print(self):
        from ph_cas.invoicing.printing import print_status

        si = make_sales_invoice()
        before = print_status("Sales Invoice", si.name)["prints"]
        build(TEST_COMPANY)
        self.assertEqual(print_status("Sales Invoice", si.name)["prints"], before)
