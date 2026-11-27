"""B96: fixes from UAT retest 5 (27 Nov 2026)."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.setup import roles as R


def _staff():
    email = "b96.staff@example.test"
    if not frappe.db.exists("User", email):
        u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "B96", "send_welcome_email": 0, "ph_provider_staff": 1})
        u.flags.ignore_permissions = True
        u.insert()
        u.add_roles(R.CASHIER_ROLE, "Accounts User", "Sales User")
    return email


class TestB96Retest5(IntegrationTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")

    def test_staff_cannot_import_suppliers(self):  # LDG-247
        from ph_cas import imports

        frappe.set_user(_staff())
        self.assertFalse(imports._may_create("Supplier"))
        self.assertTrue(imports._may_create("Customer") == bool(frappe.has_permission("Customer", "create")))
        r = {"party_type": "Supplier", "name": "B96 Supplier", "payee_type": "Non-individual", "tin": "000-777-961", "vat_status": "VAT"}
        e, _w = imports._check_party(None, r, {})
        self.assertTrue(any("You may not add a supplier" in x for x in e), e)

    def test_staff_boot_drops_actions_on_read_only_doctypes(self):  # LDG-245
        frappe.set_user(_staff())
        boot = frappe._dict(user=frappe._dict(can_create=["Journal Entry", "Sales Invoice", "Payment Entry"], can_write=["Journal Entry", "Supplier"], can_submit=["Journal Entry"]))
        R.extend_bootinfo(boot)
        self.assertNotIn("Journal Entry", boot.user.can_create)
        self.assertIn("Sales Invoice", boot.user.can_create)
        self.assertIn("Payment Entry", boot.user.can_create)
        self.assertNotIn("Supplier", boot.user.can_write)
        self.assertEqual(boot.user.can_submit, [])
        self.assertIn("Journal Entry", boot.ph_cas_read_only)
