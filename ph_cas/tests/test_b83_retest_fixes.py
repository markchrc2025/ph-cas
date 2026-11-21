"""B83: fixes from the B82 retest (build 0.1.0+5195441c14c2)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import get_first_day, get_last_day, today

from ph_cas.controls import delete_guard
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import make_journal_entry, make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY


class TestB83RetestFixes(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)

    def test_general_journal_shows_the_user_remark(self):  # LDG-210
        from ph_cas.ph_cas.report.ph_general_journal.ph_general_journal import execute as gj

        je = make_journal_entry(submit=False, amount=123)
        je.user_remark = "UAT-B83 remark"
        je.save()
        je.submit()
        frappe.db.set_value("GL Entry", {"voucher_no": je.name}, "remarks", "")
        _, rows = gj({"company": TEST_COMPANY, "from_date": get_first_day(today()), "to_date": get_last_day(today())})
        mine = [r for r in rows if r.get("debit") == 123 or r.get("credit") == 123]
        self.assertTrue(mine)
        self.assertTrue(all("UAT-B83 remark" in (r.get("particulars") or "") for r in mine))

    def test_issued_invoice_delete_gives_the_bir_message(self):  # LDG-222
        si = make_sales_invoice()
        with self.assertRaises(frappe.ValidationError) as e:
            delete_guard._guard("Sales Invoice", si.name)
        self.assertIn("has been issued and cannot be deleted", str(e.exception))
        self.assertNotIn("Cancel", str(e.exception))

    def test_draft_passes_the_guard(self):
        si = make_sales_invoice(submit=False)
        delete_guard._guard("Sales Invoice", si.name)  # no error: Frappe decides

    def test_managers_may_delete_returns(self):  # LDG-214
        perms = {p.role: p.get("delete") for p in frappe.get_meta("PH Tax Return").permissions}
        self.assertEqual(perms.get("System Manager"), 1)
        self.assertEqual(perms.get("Accounts Manager"), 1)
        self.assertFalse(perms.get("Accounts User"))
