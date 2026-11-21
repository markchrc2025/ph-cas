"""B82: fixes from the first full UAT run (build 0.1.0+1d56e40d2b40)."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.books.common import tie_row
from ph_cas.hosting import tiers
from ph_cas.invoicing import rules
from ph_cas.setup import roles as R


class TestB82UATFixes(IntegrationTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")

    def test_unbalanced_journal_is_refused_on_save(self):  # LDG-208
        doc = frappe._dict(accounts=[frappe._dict(debit=1000, credit=0), frappe._dict(debit=0, credit=900)])
        with self.assertRaises(frappe.ValidationError) as e:
            rules.validate_journal_balanced(doc)
        self.assertIn("are not equal", str(e.exception))
        rules.validate_journal_balanced(frappe._dict(accounts=[frappe._dict(debit=500, credit=0), frappe._dict(debit=0, credit=500)]))

    def test_staff_lists(self):  # LDG-183, 196, 209, 225
        self.assertEqual(R.counter_query("Administrator", "Purchase Invoice"), "")
        self.assertIn("Purchase Invoice", R.COUNTER_HIDDEN)
        self.assertNotIn("Payment Entry", R.COUNTER_HIDDEN)
        self.assertIn("Prepared Report User", R.PROFILES[R.ACCOUNTANT])  # LDG-198

    def test_users_list_leaves_out_system_accounts(self):  # LDG-170
        self.assertEqual(tiers.user_query("Administrator"), "")
        email = "b82.owner@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "B82", "send_welcome_email": 0}).insert(ignore_permissions=True)
        cond = tiers.user_query(email)
        self.assertIn("Administrator", cond)
        self.assertIn(tiers.STAFF_FIELD, cond)
        names = frappe.db.sql_list(f"select name from `tabUser` where {cond}")
        self.assertNotIn("Administrator", names)

    def test_tie_row_fills_the_shown_columns(self):  # LDG-181
        row = tie_row("Tie-out", True, "ledger 1.00", "bill_no", "supplier_name")
        self.assertTrue(row.get("bill_no"))
        self.assertTrue(row.get("supplier_name"))

    def test_book_to_tax_has_the_vat_view(self):  # LDG-212
        from ph_cas.ph_cas.report.ph_book_to_tax_reconciliation import ph_book_to_tax_reconciliation as rep

        company = frappe.get_all("Company", pluck="name", limit=1)[0]
        rows = rep.vat_rows(frappe._dict(company=company, from_date="2026-01-01", to_date="2026-12-31"))
        lines = [r["line"] for r in rows]
        self.assertIn("Output VAT per the Sales Journal", lines)
        self.assertIn("Output VAT credited in the ledger", lines)

    def test_translations_name_the_withholding_categories(self):  # LDG-182
        import csv
        import os

        path = os.path.join(frappe.get_app_path("ph_cas"), "translations", "en.csv")
        with open(path, encoding="utf-8") as f:
            have = {r[0]: r[1] for r in csv.reader(f) if r}
        for code in ("professional", "contractor", "reduced_wholesale"):
            self.assertIn(code, have)
