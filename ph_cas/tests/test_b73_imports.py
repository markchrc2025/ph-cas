"""B73 (after ECOUNT's Excel upload and Change Selected): Philippine import templates for customers,
suppliers, items, opening balances and open items, checked line by line and saved all or nothing;
batch edit of BIR fields through each record's own validation."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.qa import fullpass


class TestB73Imports(IntegrationTestCase):
    def test_imports_section(self):
        frappe.set_user("Administrator")
        for section in ("companies", "imports"):
            res = fullpass.run(section)
            failed = [f"{s['step']}: {s['detail']}" for s in res["steps"] if not s["ok"]]
            self.assertFalse(failed, f"{section}: {failed}")
