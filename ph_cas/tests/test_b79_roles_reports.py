"""B79: four role sets (Owner, Accounting Manager, Accountant, Staff), the earlier Bookkeeper and
Cashier sets renamed in place, the Reports page, and Staff kept to the counter's reports."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.qa import fullpass
from ph_cas.setup import roles as R


class TestB79RolesReports(IntegrationTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")

    def test_four_role_sets(self):
        R.setup()
        for name in R.ROLE_SETS:
            self.assertTrue(frappe.db.exists("Role Profile", name), name)
        have = lambda p: set(frappe.get_all("Has Role", filters={"parenttype": "Role Profile", "parent": p}, pluck="role"))
        self.assertIn("System Manager", have(R.OWNER))
        self.assertNotIn("System Manager", have(R.ACCOUNTING_MANAGER))
        self.assertIn("Accounting Manager", have(R.ACCOUNTING_MANAGER))
        self.assertTrue(have(R.ACCOUNTANT).isdisjoint({"System Manager", "Accounting Manager", "Accounts Manager"}))
        self.assertIn(R.CASHIER_ROLE, have(R.STAFF))

    def test_old_profiles_renamed_with_their_users(self):
        frappe.set_user("Administrator")
        for name in ("Bookkeeper",):
            if not frappe.db.exists("Role Profile", name):
                doc = frappe.new_doc("Role Profile")
                doc.role_profile = doc.name = name
                doc.db_insert()
        email = "b79.old.bookkeeper@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "B79", "send_welcome_email": 0}).insert(ignore_permissions=True)
        frappe.db.delete("User Role Profile", {"parent": email})
        row = frappe.new_doc("User Role Profile")
        row.update({"parent": email, "parenttype": "User", "parentfield": "role_profiles", "role_profile": "Bookkeeper", "idx": 1})
        row.db_insert()
        R.setup()
        self.assertFalse(frappe.db.exists("Role Profile", "Bookkeeper"))
        self.assertEqual(frappe.get_all("User Role Profile", filters={"parent": email}, pluck="role_profile"), [R.ACCOUNTANT])
        self.assertEqual(R.role_set(email), R.ACCOUNTANT)

    def test_reports_page_and_roles_sections(self):
        frappe.set_user("Administrator")
        for section in ("companies", "roles", "role_homes"):
            res = fullpass.run(section)
            failed = [f"{s['step']}: {s['detail']}" for s in res["steps"] if not s["ok"]]
            self.assertFalse(failed, f"{section}: {failed}")
