"""B04: dates, drafts, periods, inventory."""

import frappe
from frappe.utils import add_days, add_months, get_first_day, get_last_day, nowdate
from frappe.tests import IntegrationTestCase

from ph_cas.controls.dates import MANAGER_ROLE, REASON_FIELD
from ph_cas.controls.locks import PHLockError
from ph_cas.tests.fixtures import (
    acc,
    ensure_customer,
    ensure_service_item,
    ensure_stock_item,
    ensure_user,
    ensure_warehouse,
    make_journal_entry,
    make_sales_invoice,
)
from ph_cas.tests.setup import TEST_COMPANY

YESTERDAY = add_days(nowdate(), -1)
TOMORROW = add_days(nowdate(), 1)


def _je(posting_date, reason=None, submit=False):
    je = frappe.get_doc(
        {
            "doctype": "Journal Entry",
            "company": TEST_COMPANY,
            "voucher_type": "Journal Entry",
            "posting_date": posting_date,
            REASON_FIELD: reason,
            "accounts": [
                {"account": acc("Cash"), "debit_in_account_currency": 100, "cost_center": acc("Main")},
                {"account": acc("Sales"), "credit_in_account_currency": 100, "cost_center": acc("Main")},
            ],
        }
    )
    je.insert()
    if submit:
        je.submit()
    return je


class TestB04Dates(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    # D5: sales documents carry the day they are posted

    def test_sales_invoice_dated_yesterday_is_refused(self):
        with self.assertRaises(PHLockError):
            make_sales_invoice(submit=False, posting_date=YESTERDAY, set_posting_time=1)

    def test_sales_invoice_future_date_is_refused(self):
        with self.assertRaises(PHLockError):
            make_sales_invoice(submit=False, posting_date=TOMORROW, due_date=TOMORROW, set_posting_time=1)

    def test_sales_invoice_today_is_fine(self):
        si = make_sales_invoice()
        self.assertEqual(str(si.posting_date), nowdate())

    def test_payment_entry_dated_yesterday_is_refused(self):
        si = make_sales_invoice()
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        pe = get_payment_entry("Sales Invoice", si.name)
        pe.posting_date = YESTERDAY
        with self.assertRaises(PHLockError):
            pe.insert()

    # Journal Entry back-dating: manager with reason only

    def test_journal_entry_backdated_without_reason_is_refused(self):
        with self.assertRaises(PHLockError):
            _je(YESTERDAY)

    def test_journal_entry_backdated_with_reason_by_manager_is_allowed(self):
        je = _je(YESTERDAY, reason="Late bank charge found on the statement", submit=True)
        self.assertEqual(str(je.posting_date), YESTERDAY)

    def test_journal_entry_backdated_by_non_manager_is_refused_even_with_reason(self):
        user = ensure_user("ph_accounts_user@example.com", ["Accounts Manager", "Accounts User"])
        frappe.set_user(user)
        self.assertNotIn(MANAGER_ROLE, frappe.get_roles())
        with self.assertRaises(PHLockError):
            _je(YESTERDAY, reason="Trying anyway")

    def test_journal_entry_future_date_is_refused_for_everyone(self):
        with self.assertRaises(PHLockError):
            _je(TOMORROW, reason="Advance posting")

    # Drafts never print

    # frappe.get_print needs built assets, which the test bench skips, so the
    # before_print event is fired the way printview fires it.

    def test_draft_sales_invoice_cannot_be_printed(self):
        si = make_sales_invoice(submit=False)
        with self.assertRaises(PHLockError):
            si.run_method("before_print", frappe._dict())

    def test_submitted_sales_invoice_prints(self):
        si = make_sales_invoice()
        si.run_method("before_print", frappe._dict())  # no error

    # Accounting Periods

    def test_accounting_period_closes_every_posted_type_and_blocks_postings(self):
        start = get_first_day(add_months(nowdate(), -2))
        end = get_last_day(add_months(nowdate(), -2))
        name = f"_Test PH Closed {start}"
        if not frappe.db.exists("Accounting Period", f"{name} - TPC"):
            ap = frappe.get_doc(
                {
                    "doctype": "Accounting Period",
                    "period_name": name,
                    "company": TEST_COMPANY,
                    "start_date": start,
                    "end_date": end,
                    "closed_documents": [{"document_type": "Sales Invoice", "closed": 0}],
                }
            ).insert()
        else:
            ap = frappe.get_doc("Accounting Period", f"{name} - TPC")
        closed = {row.document_type: row.closed for row in ap.closed_documents}
        for dt in ("Sales Invoice", "Journal Entry", "Payment Entry", "Purchase Invoice"):
            self.assertEqual(closed.get(dt), 1, dt)
        from erpnext.accounts.general_ledger import ClosedAccountingPeriod

        with self.assertRaises(ClosedAccountingPeriod):
            _je(add_days(start, 3), reason="Posting into a closed month", submit=True)

    def test_accounting_period_cannot_exempt_a_role(self):
        start = get_first_day(add_months(nowdate(), -3))
        end = get_last_day(add_months(nowdate(), -3))
        ap = frappe.get_doc(
            {
                "doctype": "Accounting Period",
                "period_name": f"_Test PH Exempt {start}",
                "company": TEST_COMPANY,
                "start_date": start,
                "end_date": end,
                "exempted_role": "Accounts Manager",
                "closed_documents": [{"document_type": "Sales Invoice", "closed": 1}],
            }
        )
        with self.assertRaises(PHLockError):
            ap.insert()

    def test_only_the_manager_role_may_create_accounting_periods(self):
        user = ensure_user("ph_accounts_user@example.com", ["Accounts Manager", "Accounts User"])
        manager = ensure_user("ph_manager@example.com", ["Accounts Manager", MANAGER_ROLE])
        start = get_first_day(add_months(nowdate(), -4))
        end = get_last_day(add_months(nowdate(), -4))

        def attempt(period_name):
            return frappe.get_doc(
                {
                    "doctype": "Accounting Period",
                    "period_name": period_name,
                    "company": TEST_COMPANY,
                    "start_date": start,
                    "end_date": end,
                    "closed_documents": [{"document_type": "Sales Invoice", "closed": 1}],
                }
            ).insert(ignore_permissions=True)

        frappe.set_user(user)
        with self.assertRaises(PHLockError):
            attempt(f"_Test PH ByUser {start}")
        frappe.set_user(manager)
        ap = attempt(f"_Test PH ByManager {start}")
        self.assertTrue(frappe.db.exists("Accounting Period", ap.name))
        # the has_permission hook covers document-level checks
        frappe.set_user("Administrator")
        self.assertFalse(frappe.has_permission("Accounting Period", "write", doc=ap, user=user))
        self.assertTrue(frappe.has_permission("Accounting Period", "read", doc=ap, user=user))

    # D7: inventory

    def test_perpetual_inventory_is_off_and_cannot_be_enabled(self):
        self.assertEqual(frappe.db.get_value("Company", TEST_COMPANY, "enable_perpetual_inventory"), 0)
        company = frappe.get_doc("Company", TEST_COMPANY)
        company.enable_perpetual_inventory = 1
        with self.assertRaises(PHLockError):
            company.save()

    def test_stock_entry_dated_last_week_is_refused(self):
        se = frappe.get_doc(
            {
                "doctype": "Stock Entry",
                "company": TEST_COMPANY,
                "stock_entry_type": "Material Receipt",
                "purpose": "Material Receipt",
                "posting_date": add_days(nowdate(), -7),
                "set_posting_time": 1,
                "items": [
                    {"item_code": ensure_stock_item(), "qty": 1, "t_warehouse": ensure_warehouse(), "basic_rate": 10}
                ],
            }
        )
        with self.assertRaises(PHLockError):
            se.insert()

    def test_system_time_zone_is_manila(self):
        self.assertEqual(frappe.db.get_single_value("System Settings", "time_zone"), "Asia/Manila")
