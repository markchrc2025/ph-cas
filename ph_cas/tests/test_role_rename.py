"""The role PH Accounting Manager is renamed Accounting Manager (owner, 15 Nov 2026)."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.controls.dates import MANAGER_ROLE
from ph_cas.patches.v0.rename_accounting_manager_role import NEW, OLD, execute


class TestRoleRename(IntegrationTestCase):
    def test_the_role_is_accounting_manager(self):
        self.assertEqual(MANAGER_ROLE, "Accounting Manager")
        self.assertTrue(frappe.db.exists("Role", NEW))
        self.assertFalse(frappe.db.exists("Role", OLD))

    def test_holders_of_the_old_name_keep_the_role(self):
        frappe.set_user("Administrator")
        frappe.get_doc({"doctype": "Role", "role_name": OLD, "desk_access": 1}).insert(ignore_permissions=True)
        email = "_test_role_rename@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "Rename", "send_welcome_email": 0}).insert(ignore_permissions=True)
        user = frappe.get_doc("User", email)
        user.append("roles", {"role": OLD})
        user.save(ignore_permissions=True)
        execute()
        self.assertFalse(frappe.db.exists("Role", OLD))
        self.assertIn(NEW, frappe.get_roles(email))
        self.assertNotIn(OLD, frappe.get_roles(email))
