"""B76 (after ECOUNT's invoice paid to a bank and card register): Paid in full now on the Sales
Invoice (no collection receipt used), the company credit card kept out of cash, the Payment Entry
counter view."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.qa import fullpass


class TestB76Counter(IntegrationTestCase):
    def test_counter_section(self):
        frappe.set_user("Administrator")
        for section in ("companies", "purchasing", "counter"):
            res = fullpass.run(section)
            failed = [f"{s['step']}: {s['detail']}" for s in res["steps"] if not s["ok"]]
            self.assertFalse(failed, f"{section}: {failed}")
