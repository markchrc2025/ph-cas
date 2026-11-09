"""B35: subscription record, offboarding export, deletion certificate."""

import json
import os
import shutil

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from ph_cas.hosting.offboard import deletion_certificate, export_site, fiscal_years_with_postings
from ph_cas.tests.fixtures import make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY


class TestB35Offboarding(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        for n in frappe.get_all("PH Subscription", filters={"site": ["like", "_b35%"]}, pluck="name"):
            frappe.delete_doc("PH Subscription", n, force=True, ignore_permissions=True)

    def test_subscription_record_fills_tier_limits_and_builds_the_command(self):
        sub = frappe.get_doc(
            {
                "doctype": "PH Subscription",
                "client_name": "Acme Trading",
                "site": "_b35acme.ledger.sentire.solutions",
                "status": "Active",
                "tier": "Team",
                "paid_until": add_days(today(), 365),
                "max_users": 7,
            }
        ).insert(ignore_permissions=True)
        self.assertEqual(sub.max_branches, 3)
        self.assertEqual(sub.monthly_invoice_limit, 1000)
        self.assertIn("ledger-site set-tier _b35acme.ledger.sentire.solutions Team", sub.set_tier_command)
        self.assertIn("--max-users 7", sub.set_tier_command)
        self.assertNotIn("--max-branches", sub.set_tier_command)
        sub.tier = "Enterprise"
        sub.save(ignore_permissions=True)
        self.assertEqual(sub.hosting, "Dedicated pair (Enterprise)")
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({"doctype": "PH Subscription", "client_name": "X", "site": "_b35x.ledger.sentire.solutions", "status": "Ended", "tier": "Solo"}).insert(ignore_permissions=True)
        from ph_cas.ph_cas.doctype.ph_subscription.ph_subscription import due_subscriptions

        sub.status = "Active"
        sub.paid_until = add_days(today(), -1)
        sub.save(ignore_permissions=True)
        self.assertIn(sub.name, due_subscriptions())

    def test_export_site_produces_backup_books_registration_audit_and_manifest(self):
        make_sales_invoice(submit=True)
        self.assertIn(int(today()[:4]), fiscal_years_with_postings(TEST_COMPANY))
        target = frappe.get_site_path("private", "offboarding", "_b35_test")
        if os.path.exists(target):
            shutil.rmtree(target)
        try:
            out = export_site(target)
            files = out["manifest"]["files"]
            self.assertTrue(any(k.startswith("01_backup/") and k.endswith("-database.sql.gz") for k in files), list(files)[:5])
            self.assertTrue(any(k.startswith("02_books/") and k.endswith("TRANSMITTAL.txt") for k in files))
            self.assertTrue(any(k.startswith("03_registration/") and "Annex_B" in k for k in files))
            self.assertIn("04_audit/event_log.csv", files)
            self.assertIn("05_registers/sales_invoice.csv", files)
            self.assertTrue(os.path.exists(os.path.join(target, "EXPORT-MANIFEST.json")))
            self.assertTrue(os.path.exists(os.path.join(target, "README.txt")))
            m = json.load(open(os.path.join(target, "EXPORT-MANIFEST.json")))
            self.assertEqual(m["site"], frappe.local.site)
            for rel, meta in m["files"].items():
                self.assertEqual(len(meta["sha256"]), 64, rel)
                self.assertTrue(os.path.exists(os.path.join(target, rel)), rel)
            with open(os.path.join(target, "05_registers/sales_invoice.csv"), encoding="utf-8") as f:
                head = f.readline()
            self.assertIn("bir_serial", head)
        finally:
            shutil.rmtree(target, ignore_errors=True)

    def test_deletion_certificate_names_site_client_and_dates(self):
        txt = deletion_certificate("acme.ledger.sentire.solutions", "Acme Trading", "MCRC Tax and Accounting Services", deleted_on="2027-01-31", export_accepted_on="2027-01-15", signatory="C. Canlubo", position="Managing Partner")
        for s in ("acme.ledger.sentire.solutions", "Acme Trading", "2027-01-31", "2027-01-15", "C. Canlubo, Managing Partner", "Revenue District Office"):
            self.assertIn(s, txt)
        self.assertNotIn("—", txt)
