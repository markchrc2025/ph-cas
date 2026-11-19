"""B72 (after ECOUNT's payment journal): Record an expense posts one paid bill with input VAT worked
back from the receipt, EWT on the net, the 2307 owed, never on cost of goods sold by default, and
not by a Cashier."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.qa import fullpass


class TestB72Expense(IntegrationTestCase):
    def test_expense_section(self):
        frappe.set_user("Administrator")
        for section in ("companies", "purchasing", "expense"):
            res = fullpass.run(section)
            failed = [f"{s['step']}: {s['detail']}" for s in res["steps"] if not s["ok"]]
            self.assertFalse(failed, f"{section}: {failed}")
