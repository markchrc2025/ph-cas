"""B86: fixes from retest 2 (build 0.1.0+b8680cc281fc)."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas import branding
from ph_cas.setup import roles


class TestB86Retest2Fixes(IntegrationTestCase):
    def test_every_role_set_may_cancel_invoices_and_receipts(self):  # LDG-235
        roles.grant_cancel()
        roles.grant_cancel()  # idempotent
        for doctype, role in roles.CANCEL_RIGHTS:
            perms = frappe.get_all("Custom DocPerm", filters={"parent": doctype, "role": role, "permlevel": 0}, pluck="cancel") or frappe.get_all(
                "DocPerm", filters={"parent": doctype, "role": role, "permlevel": 0}, pluck="cancel"
            )
            self.assertEqual(perms[0], 1, f"{role} cancel on {doctype}")
        for set_name in (roles.ACCOUNTANT, roles.STAFF):
            self.assertIn("Accounts User", roles.PROFILES[set_name])

    def test_login_page_shows_the_wordmark(self):  # LDG-238
        old = getattr(frappe.local, "path", None)
        frappe.local.path = "login"
        try:
            ctx = branding.website_context(frappe._dict(title="Login", logo=branding.ASSETS["logo"]))
        finally:
            frappe.local.path = old
        self.assertEqual(ctx["logo"], branding.ASSETS["wordmark"])
        self.assertTrue(ctx["title"].startswith(branding.product_name()))
