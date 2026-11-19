"""B75 (after ECOUNT's per-user dashboards and Help menu): a home per role set (the Cashier sees the
counter, not the payables or the tax position), Help > Your plan and Help > Get help."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.qa import fullpass


class TestB75RoleHomes(IntegrationTestCase):
    def test_role_homes_section(self):
        frappe.set_user("Administrator")
        for section in ("companies", "role_homes"):
            res = fullpass.run(section)
            failed = [f"{s['step']}: {s['detail']}" for s in res["steps"] if not s["ok"]]
            self.assertFalse(failed, f"{section}: {failed}")
