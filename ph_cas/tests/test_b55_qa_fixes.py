"""B55: fixes from the first staging QA pass (LDG issues in the B55 PR).

- Prints from the print page and PDF (GET requests) are recorded and committed;
  the desk's on-screen preview records nothing (REPRINT counting).
- The seller's registered address (per COR) prints on invoices and the BIR header.
- The 1601-EQ credits only what the filed 0619-E returns remitted.
- A customer payment allocated in full but received net of the tax withheld books
  the withheld tax instead of failing on "Difference Amount must be zero".
- The cash books balance on their face; the journals name credit notes and
  collection receipts.
"""

from types import SimpleNamespace

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_months, flt, get_first_day, getdate, today

from ph_cas.audit.header import company_facts
from ph_cas.forms.withholding import remitted_0619e
from ph_cas.invoicing.printing import is_screen_preview, print_status
from ph_cas.setup.chart import account_for, setup_philippine_company
from ph_cas.tests.fixtures import ensure_service_item
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _set_regime
from ph_cas.tests.test_b13_customer_withholding import _customer


class _Request:
    """Stands in for the HTTP request whose path tells a print from a preview."""

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.before = getattr(frappe.local, "request", None)
        self.flags_commit = frappe.local.flags.get("commit")
        frappe.local.request = SimpleNamespace(path=self.path)
        frappe.local.flags.commit = False
        return self

    def __exit__(self, *exc):
        frappe.local.request = self.before
        frappe.local.flags.commit = self.flags_commit


class TestB55QAFixes(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")
        frappe.db.set_value("Company", TEST_COMPANY, {"tax_id": "123-456-789", "ph_taxpayer_type": "Non-individual"}, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)

    def tearDown(self):
        _set_regime("Non-VAT")

    # ---- REPRINT counting -------------------------------------------------------------------
    def test_the_print_page_records_and_commits_and_the_preview_does_not(self):
        si = _invoice([(ensure_service_item(), 1, 1000, {})], submit=True)
        self.assertEqual(print_status("Sales Invoice", si.name)["prints"], 0)

        with _Request("/api/method/frappe.www.printview.get_html_and_style"):
            self.assertTrue(is_screen_preview())
            doc = frappe.get_doc("Sales Invoice", si.name)
            doc.run_method("before_print", frappe._dict())
            self.assertEqual(print_status("Sales Invoice", si.name)["prints"], 0)  # nothing recorded
            self.assertEqual(doc.ph_print_no, 1)  # it shows what the next print will be
            self.assertFalse(doc.ph_is_reprint)
            self.assertTrue(doc.ph_screen_preview)
            self.assertFalse(frappe.local.flags.commit)

        with _Request("/printview"):
            self.assertFalse(is_screen_preview())
            doc = frappe.get_doc("Sales Invoice", si.name)
            doc.run_method("before_print", frappe._dict())
            self.assertEqual(print_status("Sales Invoice", si.name)["prints"], 1)
            self.assertFalse(doc.ph_is_reprint)
            self.assertTrue(frappe.local.flags.commit)  # a GET request keeps the record

        with _Request("/api/method/frappe.utils.print_format.download_pdf"):
            doc = frappe.get_doc("Sales Invoice", si.name)
            doc.run_method("before_print", frappe._dict())
            self.assertEqual(print_status("Sales Invoice", si.name)["prints"], 2)
            self.assertTrue(doc.ph_is_reprint)
            self.assertEqual(doc.ph_print_no, 2)

        with _Request("/printpreview"):
            doc = frappe.get_doc("Sales Invoice", si.name)
            doc.run_method("before_print", frappe._dict())
            self.assertEqual(doc.ph_print_no, 3)
            self.assertTrue(doc.ph_is_reprint)
            self.assertEqual(print_status("Sales Invoice", si.name)["prints"], 2)
        events = frappe.get_all("PH Event Log", filters={"event": "print", "ref_name": si.name}, pluck="name")
        self.assertEqual(len(events), 2)  # the two prints, not the previews

    def test_the_preview_says_it_is_not_a_printed_copy(self):
        si = _invoice([(ensure_service_item(), 1, 1000, {})], submit=True)
        pf = frappe.get_doc("Print Format", "PH Sales Invoice")
        with _Request("/api/method/frappe.www.printview.get_html_and_style"):
            doc = frappe.get_doc("Sales Invoice", si.name)
            doc.run_method("before_print", frappe._dict())
            html = frappe.render_template(pf.html, {"doc": doc})
        self.assertIn("PREVIEW ON SCREEN, NOT A PRINTED COPY", html)
        self.assertIn("the ORIGINAL", html)

    # ---- seller address -----------------------------------------------------------------------
    def test_the_registered_address_prints(self):
        frappe.db.set_value("Company", TEST_COMPANY, {"ph_registered_address": "Unit 5, 88 Tala Street\nBarangay San Antonio, Pasig City", "ph_zip": "1605"}, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        try:
            self.assertEqual(company_facts(TEST_COMPANY)["address"], "Unit 5, 88 Tala Street, Barangay San Antonio, Pasig City 1605")
            si = _invoice([(ensure_service_item(), 1, 1000, {})], submit=True)
            si.run_method("before_print", frappe._dict())
            html = frappe.render_template(frappe.get_doc("Print Format", "PH Sales Invoice").html, {"doc": si})
            self.assertIn("88 Tala Street", html)
            self.assertNotIn("(address not set)", html)
        finally:
            frappe.db.set_value("Company", TEST_COMPANY, {"ph_registered_address": None, "ph_zip": None}, update_modified=False)
            frappe.clear_document_cache("Company", TEST_COMPANY)

    # ---- 1601-EQ remittances -------------------------------------------------------------------
    def test_1601eq_credits_only_the_filed_0619e(self):
        month = get_first_day(add_months(getdate(today()), 60))  # a month nothing was filed for
        self.assertEqual(remitted_0619e(TEST_COMPANY, month), (0, None))
        ret = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "0619-E", "period_key": month.strftime("%Y-%m"), "period_start": month, "docstatus": 1, "name": f"_QA-0619E-{month:%Y%m}"})
        ret.db_insert()
        frappe.get_doc({"doctype": "PH Tax Return Line", "parent": ret.name, "parenttype": "PH Tax Return", "parentfield": "lines", "item": "14", "label": "Amount of Remittance", "amount": 1234.5, "name": f"_QA-0619E-L-{month:%Y%m}"}).db_insert()
        amount, name = remitted_0619e(TEST_COMPANY, month)
        self.assertEqual(flt(amount), 1234.5)
        self.assertEqual(name, ret.name)

    # ---- customer payment net of withholding, allocated in full -------------------------------
    def test_full_allocation_with_net_cash_books_the_withheld_tax(self):
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        twa = _customer("_Test PH TWA Corp", ph_top_withholding_agent=1)
        si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=twa, submit=True)
        self.assertEqual(flt(si.ph_wht_amount), 20)
        pe = get_payment_entry("Sales Invoice", si.name)
        pe.paid_amount = 1100
        pe.received_amount = 1100
        pe.references[0].allocated_amount = 1120  # the invoice, allocated in full
        pe.insert()
        self.assertEqual(flt(pe.ph_wht_deducted), 20)
        self.assertEqual(flt(pe.references[0].allocated_amount), 1120)
        self.assertEqual(flt(pe.difference_amount), 0)
        pe.save()  # validating again changes nothing
        self.assertEqual(flt(pe.ph_wht_deducted), 20)
        self.assertEqual(len(pe.deductions), 1)
        pe.submit()
        self.assertEqual(flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount")), 0)

        # the cash receipts book shows the withheld tax as the other debit, so the receipt balances
        from ph_cas.ph_cas.report.ph_cash_receipts_book.ph_cash_receipts_book import execute as crb

        cols, rows = crb({"company": TEST_COMPANY, "from_date": today(), "to_date": today()})
        mine = [r for r in rows if r.get("reference") == pe.bir_serial]
        self.assertTrue(mine)
        start = rows.index(mine[0])
        group = [mine[0]]
        for r in rows[start + 1:]:
            if r.get("reference"):
                break
            group.append(r)
        debit = flt(mine[0]["cash_debit"]) + sum(flt(r.get("other_debit")) for r in group)
        credit = sum(flt(r.get("credit")) for r in group)
        self.assertEqual(flt(debit, 2), flt(credit, 2))
        self.assertIn(account_for(TEST_COMPANY, "cwt_receivable"), [r.get("other_debit_account") for r in group])

    def test_full_allocation_short_by_more_than_the_tax_still_refuses(self):
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        twa = _customer("_Test PH TWA Corp", ph_top_withholding_agent=1)
        si = _invoice([(ensure_service_item(), 1, 1000, {})], customer=twa, submit=True)
        pe = get_payment_entry("Sales Invoice", si.name)
        pe.paid_amount = 900
        pe.received_amount = 900
        pe.references[0].allocated_amount = 1120
        pe.insert()
        self.assertEqual(flt(pe.ph_wht_deducted), 0)
        with self.assertRaises(frappe.ValidationError):
            pe.submit()

    # ---- journals name the document --------------------------------------------------------
    def test_the_general_journal_names_credit_notes(self):
        from ph_cas.books.common import voucher_kind

        si = _invoice([(ensure_service_item(), 1, 1000, {})], submit=True)
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

        cn = make_sales_return(si.name)
        cn.insert()
        cn.submit()
        cache = {}
        self.assertEqual(voucher_kind("Sales Invoice", si.name, cache), "Sales Invoice")
        self.assertEqual(voucher_kind("Sales Invoice", cn.name, cache), "Credit Note")
        from ph_cas.ph_cas.report.ph_general_journal.ph_general_journal import execute as gj

        cols, rows = gj({"company": TEST_COMPANY, "from_date": today(), "to_date": today()})
        self.assertIn("Credit Note", {r.get("voucher_type") for r in rows})

    # ---- compliance calendar ------------------------------------------------------------------
    def test_calendar_flags_a_computed_return_past_due_and_skips_periods_before_the_books(self):
        from unittest.mock import patch

        from frappe.utils import add_days, get_last_day

        from ph_cas.tax import calendar as cal
        from ph_cas.tax.returns import get_or_create

        start = cal.books_start(TEST_COMPANY)
        earlier = [r for r in cal.calendar(TEST_COMPANY, start.year - 1) if not r.get("figures")]
        self.assertEqual(earlier, [])  # a year before the books began lists nothing as overdue

        ms = get_first_day(today())
        get_or_create(TEST_COMPANY, "0619-E", ms, get_last_day(ms))
        later = add_days(get_last_day(add_months(ms, 1)), 1)  # past the 10th of next month
        with patch("frappe.utils.nowdate", return_value=str(later)):
            rows = [r for r in cal.calendar(TEST_COMPANY, ms.year) if r["form"] == "0619-E" and getdate(r["period_start"]) == ms]
        if ms.month % 3:  # months 1 and 2 of a quarter have a 0619-E
            self.assertEqual(rows[0]["status"], "OVERDUE, computed, not filed")


class TestB56TaxBreakup(IntegrationTestCase):
    """LDG-112: output and input VAT sit only on the lines they belong to."""

    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("VAT")

    def tearDown(self):
        _set_regime("Non-VAT")

    def test_output_vat_is_not_spread_over_exempt_or_zero_rated_lines(self):
        from ph_cas.tests.test_b12_sales_vat import _item

        si = _invoice([(_item("_PH VATable", "VATable"), 2, 15000, {}), (_item("_PH Exempt", "VAT-exempt"), 5, 300, {}), (_item("_PH Zero", "Zero-rated"), 1, 1000, {})], submit=True)
        self.assertEqual(flt(si.ph_vat_amount), 3600)
        by_item = {}
        for d in si.item_wise_tax_details:
            row = next(i for i in si.items if i.name == d.item_row)
            by_item[row.item_code] = by_item.get(row.item_code, 0) + flt(d.amount)
        self.assertEqual(flt(by_item.get("_PH VATable"), 2), 3600)
        self.assertEqual(flt(by_item.get("_PH Exempt", 0), 2), 0)
        self.assertEqual(flt(by_item.get("_PH Zero", 0), 2), 0)
        self.assertEqual(flt(si.grand_total), 35100 + 1000)
        gl = frappe.db.get_value("GL Entry", {"voucher_no": si.name, "account": account_for(TEST_COMPANY, "output_vat"), "is_cancelled": 0}, "credit")
        self.assertEqual(flt(gl), 3600)

    def test_input_vat_sits_on_its_own_kind_of_line(self):
        from ph_cas.tests.fixtures import ensure_supplier_profile, make_purchase_invoice
        from ph_cas.tests.test_b12_sales_vat import _item

        sup = ensure_supplier_profile("_Test PH VAT Supplier B56", ph_vat_status="VAT", ph_ewt_category="None (no withholding)")
        pi = make_purchase_invoice(sup, [(_item("_PH VATable", "VATable"), 1, 10000, {}), (_item("_PH Exempt", "VAT-exempt"), 1, 500, {})], submit=True)
        exempt_row = next(i for i in pi.items if i.item_code == "_PH Exempt")
        on_exempt = sum(flt(d.amount) for d in pi.item_wise_tax_details if d.item_row == exempt_row.name)
        self.assertEqual(flt(on_exempt, 2), 0)
        self.assertEqual(flt(pi.ph_input_vat_goods) + flt(pi.ph_input_vat_services), 1200)


class TestB56Exports(IntegrationTestCase):
    def test_an_event_asks_for_the_commit_so_a_download_keeps_it(self):
        from ph_cas.audit.events import record

        frappe.set_user("Administrator")
        frappe.local.flags.commit = False
        record("export", "Company", TEST_COMPANY, 0, {"test": "b56"})
        self.assertTrue(frappe.local.flags.commit)
        frappe.local.flags.commit = False

    def test_1604e_takes_the_top_agent_answer_from_the_company(self):
        frappe.set_user("Administrator")
        frappe.db.set_value("Company", TEST_COMPANY, "ph_top_withholding_agent", 1, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        try:
            ret = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "1604-E", "period_key": str(getdate(today()).year)})
            ret.insert()
            ret.refresh_from_books()
            import json

            self.assertEqual(json.loads(ret.data)["topAgent"], "yes")
            self.assertNotIn("topAgent", ret.needs or "")
        finally:
            frappe.db.set_value("Company", TEST_COMPANY, "ph_top_withholding_agent", 0, update_modified=False)
            frappe.clear_document_cache("Company", TEST_COMPANY)

    def test_sawt_takes_the_form_names_bir_returns_uses(self):
        from ph_cas.dat.sawt import build

        frappe.set_user("Administrator")
        frappe.db.set_value("Company", TEST_COMPANY, {"tax_id": "123-456-789", "ph_branch_code": "00000", "ph_rdo": "045", "ph_registered_name": "SAMPLE TAXPAYER CORP"}, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        name, content, n = build(TEST_COMPANY, "1702-RT", "2026-01-01", "2026-12-31")
        self.assertIn(b"H1702RT", content)
        self.assertTrue(name.endswith("1702RT.DAT"))


class TestB57CashBooksNet(IntegrationTestCase):
    def test_a_receivable_raised_and_settled_in_one_voucher_drops_out(self):
        from ph_cas.books.common import net_by_account

        L = frappe._dict
        lines = [  # a cash sale: the receivable is raised and settled in the same invoice
            L(account="Debtors", debit=1620, credit=0), L(account="Sales", debit=0, credit=1500), L(account="Output VAT", debit=0, credit=120),
            L(account="Cash", debit=1620, credit=0), L(account="Debtors", debit=0, credit=1620),
        ]
        out = net_by_account(lines, skip={"Cash"})
        self.assertEqual([(r.account, r.debit, r.credit) for r in out], [("Sales", 0.0, 1500.0), ("Output VAT", 0.0, 120.0)])
        collection = [L(account="Cash", debit=34470, credit=0), L(account="CWT", debit=630, credit=0), L(account="Debtors", debit=0, credit=35100)]
        out = net_by_account(collection, skip={"Cash"})
        self.assertEqual([(r.account, r.debit, r.credit) for r in out], [("CWT", 630.0, 0.0), ("Debtors", 0.0, 35100.0)])
