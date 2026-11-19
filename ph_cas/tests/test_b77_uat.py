"""B77 (Sentire UAT Standard v1.0): the build stamp, the UAT accounts kept to their companies, and
staging mail going only to the test mailbox."""

import os
import subprocess

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas import buildstamp
from ph_cas.qa import uat

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestB77UAT(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.local.conf.ph_staging_site = 1

    def tearDown(self):
        frappe.local.conf.pop("ph_staging_site", None)
        frappe.set_user("Administrator")
        # the seed commits; switch the UAT accounts off again so later tests' user limits hold
        for a in uat.accounts():
            if frappe.db.exists("User", a["email"]):
                frappe.db.set_value("User", a["email"], "enabled", 0)
        frappe.db.commit()

    def test_build_stamp(self):
        info = uat.build_info()
        self.assertTrue(info["build"].startswith(info["version"] + "+"))
        self.assertEqual(len(info["build"].split("+")[1]), 12)

    def test_build_stamp_ignores_caches_and_matches_git(self):
        if not os.path.isdir(os.path.join(ROOT, ".git")):
            self.skipTest("no git checkout")
        dirty = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", "ph_cas"], capture_output=True, text=True).stdout.strip()
        if dirty:
            self.skipTest("uncommitted changes under ph_cas")
        self.assertEqual(buildstamp.from_disk(), buildstamp.from_git("HEAD", ROOT))

    def test_accounts_kept_to_their_companies(self):
        if not frappe.db.exists("Company", uat.COMPANY_A):  # the demo company exists on staging only
            uat.COMPANY_A = frappe.get_all("Company", filters={"name": ("not like", "UAT%")}, pluck="name", limit=1)[0]
        os.environ["STAGING_UAT_PASSWORD"] = "Uat#Test-2026-local"
        try:
            uat.seed_uat()
            rows = {r["user"]: r for r in uat.check_accounts()}
        finally:
            os.environ.pop("STAGING_UAT_PASSWORD", None)
        b = uat._plus("uat-accountant-b")
        self.assertTrue(all(r["signs_in"] and r["enabled"] for r in rows.values()), rows)
        self.assertEqual({rows[uat._plus(t)]["role_set"] for t in ("uat-owner-a", "uat-acctmgr-a", "uat-accountant-a", "uat-staff-a")},
                         {"Owner", "Accounting Manager", "Accountant", "Staff"})
        self.assertEqual(rows[b]["companies"], [uat.COMPANY_B])
        frappe.set_user(b)
        self.assertFalse(frappe.has_permission("Company", "read", uat.COMPANY_A))
        self.assertTrue(frappe.has_permission("Company", "read", uat.COMPANY_B))
        from ph_cas.books.cash import cash_position

        with self.assertRaises(frappe.PermissionError):
            cash_position(uat.COMPANY_A)
        cash_position(uat.COMPANY_B)

    def test_staging_mail_goes_to_the_test_mailbox(self):
        q = frappe.get_doc({"doctype": "Email Queue", "sender": "noreply@example.com", "message": "x",
                            "recipients": [{"recipient": "client@example.com"}, {"recipient": "other@example.com"}], "show_as_cc": "cc@example.com"})
        uat.redirect_staging_mail(q)
        self.assertEqual({r.recipient for r in q.recipients}, {uat.TEST_MAILBOX})
        self.assertFalse(q.show_as_cc)
