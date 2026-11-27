"""B94: fixes from the owner's human tests of 25 to 27 Nov 2026."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.controls import delete_guard
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import make_journal_entry
from ph_cas.tests.setup import TEST_COMPANY


class TestB94Batch(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)

    def test_form_delete_of_a_cancelled_journal_gives_the_posted_message(self):  # JP-003
        je = make_journal_entry(amount=77)
        je.cancel()
        with self.assertRaises(frappe.ValidationError) as e:
            delete_guard.get_linked_docs_to_delete("Journal Entry", je.name)
        self.assertIn("has been posted and cannot be deleted", str(e.exception))
        self.assertIn("ph_cas.controls.delete_guard.get_linked_docs_to_delete", frappe.get_hooks("override_whitelisted_methods").get("frappe.desk.form.linked_with.get_linked_docs_to_delete", []))

    def test_staff_reads_bills_journals_suppliers_and_returns_but_changes_none(self):  # BR-005 note
        from ph_cas.setup import roles as R

        email = "b94.staff@example.test"
        if not frappe.db.exists("User", email):
            u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "B94", "send_welcome_email": 0, "ph_provider_staff": 1})
            u.flags.ignore_permissions = True
            u.insert()
            u.add_roles(R.CASHIER_ROLE, "Accounts User", "Sales User")
        for dt in ("Purchase Invoice", "Journal Entry", "Supplier", "PH Tax Return", "PH 2307 Issued"):
            self.assertTrue(R.cashier_limit(dt, "read", email), dt)
            self.assertFalse(R.cashier_limit(dt, "create", email), dt)
            self.assertFalse(R.cashier_limit(dt, "write", email), dt)
            self.assertEqual(R.counter_query(email, dt), "")
        self.assertFalse(R.cashier_limit(frappe._dict(doctype="Payment Entry", payment_type="Pay"), "create", email))
        self.assertIn("PH Approval Chain", R.COUNTER_HIDDEN)

    def _withheld_invoice(self):
        from ph_cas.tests.fixtures import make_sales_invoice

        si = make_sales_invoice(rate=10000)
        frappe.db.set_value("Sales Invoice", si.name, {"ph_wht_atc": "WC160", "ph_wht_base": 10000, "ph_wht_amount": 200})
        return frappe.get_doc("Sales Invoice", si.name)

    def test_customer_2307_from_the_invoice_feeds_the_income_tax_return(self):
        from frappe.utils import getdate

        from ph_cas.tax import received_2307 as R2

        si = self._withheld_invoice()
        start, end = R2._quarter_bounds(si.posting_date)
        self.assertIn(si.name, [r.name for r in R2.missing(si.company, start, end)])
        self.assertTrue(any(si.name in w for w in R2.warnings_for("1702Q", si.company, start.replace(month=1), end)))
        self.assertEqual(R2.warnings_for("2550Q", si.company, start, end), [])  # VAT return: no 2307 note
        import io as _io

        from pypdf import PdfWriter

        w = PdfWriter()
        w.add_blank_page(width=612, height=936)
        buf = _io.BytesIO()
        w.write(buf)
        f = frappe.get_doc({"doctype": "File", "file_name": "b94-2307.pdf", "is_private": 1, "content": buf.getvalue()}).insert(ignore_permissions=True)
        name = R2.record_for_invoice(si.name, f.file_url, "wc160", 10000, 200)
        doc = frappe.get_doc("PH 2307 Received", name)
        self.assertEqual((doc.docstatus, doc.lines[0].atc, doc.total_tax, doc.invoices[0].sales_invoice), (1, "WC160", 200, si.name))
        m = R2.for_invoice(si.name)
        self.assertEqual((m["withheld"], [r["name"] for r in m["received"]]), (200, [name]))
        self.assertNotIn(si.name, [r.name for r in R2.missing(si.company, start, end)])
        zname, content = R2.attachments_zip(si.company, start, end)
        import io
        import zipfile

        z = zipfile.ZipFile(io.BytesIO(content))
        self.assertIn("00_INDEX.csv", z.namelist())
        self.assertTrue(any(n.startswith(name) for n in z.namelist()))
        self.assertEqual(getdate(doc.period_from), start)

    def test_bill_shows_its_2307(self):
        from ph_cas.ph_cas.doctype.ph_2307_issued import ph_2307_issued as I
        from ph_cas.tests.test_b26_2307 import TestB26_2307
        from ph_cas.tests.fixtures import ensure_service_item, make_purchase_invoice

        TestB26_2307.setUp(self)
        pi = make_purchase_invoice(self.sup, [(ensure_service_item(), 1, 10000, {})], submit=True)
        name = I.make_for_document("Purchase Invoice", pi.name)
        self.assertIn(name, [c["name"] for c in I.for_document("Purchase Invoice", pi.name)])
