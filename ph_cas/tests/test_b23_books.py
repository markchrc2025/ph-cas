"""B23: General Journal, General Ledger, Cash Receipts and Cash Disbursements books."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, get_first_day, get_last_day, today

from ph_cas.audit.export import csv_with_header
from ph_cas.books.common import period_totals
from ph_cas.ph_cas.report.ph_cash_disbursements_book.ph_cash_disbursements_book import execute as cdb
from ph_cas.ph_cas.report.ph_cash_receipts_book.ph_cash_receipts_book import execute as crb
from ph_cas.ph_cas.report.ph_general_journal.ph_general_journal import execute as gj
from ph_cas.ph_cas.report.ph_general_ledger_book.ph_general_ledger_book import execute as glb
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import acc, make_journal_entry, make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY


class TestB23Books(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        self.f = {"company": TEST_COMPANY, "from_date": get_first_day(today()), "to_date": get_last_day(today())}
        make_journal_entry()
        si = make_sales_invoice()
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        pe = get_payment_entry("Sales Invoice", si.name)
        pe.reference_no = "DEP-1"
        pe.reference_date = today()
        pe.insert()
        pe.submit()
        self.pe = pe
        self.si = si

    def test_general_journal_ties_to_the_ledger(self):
        cols, rows = gj(self.f)
        total = [r for r in rows if r.get("is_total_row")][0]
        t = period_totals(TEST_COMPANY, self.f["from_date"], self.f["to_date"])
        self.assertEqual(flt(total["debit"]), t["debit"])
        self.assertEqual(flt(total["credit"]), t["credit"])
        self.assertEqual(flt(total["debit"]), flt(total["credit"]))
        self.assertIn("TIES TO THE LEDGER", rows[-1]["particulars"])
        self.assertIn(self.si.bir_serial, [r.get("reference") for r in rows])

    def test_general_ledger_running_balance_and_closing_tie(self):
        cols, rows = glb({**self.f, "account": acc("Cash")})
        self.assertEqual(rows[0]["particulars"], "Opening balance")
        closing = [r for r in rows if r.get("is_closing")][0]
        self.assertIn("ties", closing["particulars"])
        bal = rows[0]["balance"]
        for r in rows[1:-1]:
            bal = flt(bal + flt(r["debit"]) - flt(r["credit"]), 2)
            self.assertEqual(flt(r["balance"]), bal)
        self.assertEqual(flt(closing["balance"]), bal)

    def test_cash_receipts_book_shows_the_collection_receipt(self):
        cols, rows = crb(self.f)
        refs = [r.get("reference") for r in rows if r.get("reference")]
        self.assertIn(self.pe.bir_serial, refs)
        self.assertIn("TIES TO THE LEDGER", rows[-1]["particulars"])
        row = [r for r in rows if r.get("reference") == self.pe.bir_serial][0]
        self.assertEqual(flt(row["cash_debit"]), flt(self.pe.paid_amount))
        self.assertEqual(row["credit_account"], acc("Debtors"))

    def test_cash_disbursements_book_ties(self):
        from ph_cas.tests.fixtures import ensure_supplier_profile, make_purchase_invoice, ensure_service_item

        sup = ensure_supplier_profile("_Test PH NonVAT Supplier", ph_vat_status="Non-VAT", ph_ewt_category="None (no withholding)")
        pi = make_purchase_invoice(sup, [(ensure_service_item(), 1, 700, {})], submit=True)
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        pe = get_payment_entry("Purchase Invoice", pi.name)
        pe.reference_no = "CHK-1001"
        pe.reference_date = today()
        pe.insert()
        pe.submit()
        cols, rows = cdb(self.f)
        self.assertIn("TIES TO THE LEDGER", rows[-1]["particulars"])
        row = [r for r in rows if r.get("reference") and "CHK-1001" in r["reference"]][0]
        self.assertEqual(flt(row["cash_credit"]), 700)
        self.assertEqual(row["debit_account"], acc("Creditors"))

    def test_export_carries_the_header(self):
        cols, rows = gj(self.f)
        data = csv_with_header([c["label"] for c in cols], [[r.get(c["fieldname"]) for c in cols] for r in rows], TEST_COMPANY).decode("utf-8-sig")
        self.assertIn("Software: PH CAS", data.split("\r\n")[3])
        self.assertIn("Date,Reference,Document,Particulars,Account,Debit,Credit", data)
