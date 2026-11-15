"""B33: open demo access and pilots."""

import csv
import os

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_to_date, now_datetime, today

from ph_cas.hosting import demo_access
from ph_cas.hosting.demo_access import (
    DEMO_ROLE,
    consume_token,
    daily_pilot_check,
    expire_demo_users,
    is_demo_site,
    request_access,
)
from ph_cas.hosting.tiers import set_tier


class TestB33Demo(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.conf.ph_demo_site = 1
        frappe.flags.mute_emails = True
        self.log = demo_access._log_path()
        if os.path.exists(self.log):
            os.remove(self.log)

    def tearDown(self):
        frappe.conf.pop("ph_demo_site", None)
        frappe.flags.mute_emails = False
        if os.path.exists(self.log):
            os.remove(self.log)
        for u in frappe.get_all("User", filters={"name": ["like", "_b33_%"]}, pluck="name"):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        set_tier("Internal", subscription_until="", pilot_until="")
        frappe.db.commit()

    def test_role_exists_and_demo_flag_is_read_from_site_config(self):
        self.assertTrue(frappe.db.exists("Role", DEMO_ROLE))
        self.assertTrue(is_demo_site())
        frappe.conf.ph_cas_production = 1
        try:
            self.assertFalse(is_demo_site())  # production is never a demo
        finally:
            frappe.conf.pop("ph_cas_production", None)

    def test_request_creates_restricted_user_logs_lead_and_issues_token(self):
        out = request_access("Maria Santos", "_b33_maria@example.com", company="Santos Hardware", mobile="0917")
        self.assertTrue(out["ok"])
        u = frappe.get_doc("User", "_b33_maria@example.com")
        self.assertTrue(u.enabled)
        self.assertIn(DEMO_ROLE, [r.role for r in u.roles])
        self.assertTrue(u.ph_provider_staff)  # demo seats never count against a tier
        perms = frappe.get_all("User Permission", filters={"user": u.name, "allow": "Company"}, pluck="for_value")
        self.assertEqual(len(perms), 1)
        self.assertTrue(perms[0].startswith("Santos Hardware ("))
        self.assertTrue(frappe.db.exists("Company", perms[0]))
        rows = list(csv.DictReader(open(self.log, encoding="utf-8")))
        self.assertEqual(rows[0]["email"], "_b33_maria@example.com")
        self.assertEqual(rows[0]["demo_company"], perms[0])
        # the token in the cache resolves to the user while valid
        keys = [k for k in frappe.cache().get_keys(demo_access.TOKEN_PREFIX + "*")]
        self.assertTrue(keys)
        token = keys[-1].decode() if isinstance(keys[-1], bytes) else keys[-1]
        token = token.split(demo_access.TOKEN_PREFIX, 1)[1]
        self.assertEqual(consume_token(token), u.name)
        self.assertIsNone(consume_token("not-a-token"))

    def test_second_request_for_the_same_email_within_30_days_is_refused(self):
        request_access("Jose Cruz", "_b33_jose@example.com")
        with self.assertRaises(frappe.ValidationError):
            request_access("Jose Cruz", "_b33_jose@example.com")

    def test_request_is_refused_outside_a_demo_site(self):
        frappe.conf.pop("ph_demo_site", None)
        with self.assertRaises(frappe.PermissionError):
            request_access("Ana Lim", "_b33_ana@example.com")

    def test_expired_demo_users_are_disabled_by_the_hourly_job(self):
        request_access("Ben Tan", "_b33_ben@example.com")
        rows = list(csv.DictReader(open(self.log, encoding="utf-8")))
        rows[0]["expires_on"] = str(add_to_date(now_datetime(), hours=-1))[:19]
        with open(self.log, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        self.assertEqual(expire_demo_users(), 1)
        self.assertFalse(frappe.db.get_value("User", "_b33_ben@example.com", "enabled"))

    def test_pilot_check_counts_down_then_switches_users_off(self):
        set_tier("Team", pilot_until=add_days(today(), -5))
        st = daily_pilot_check()
        self.assertTrue(st["pilot"])
        self.assertEqual(st["days_left"], 25)
        set_tier("Team", pilot_until=add_days(today(), -31))
        u = frappe.get_doc(
            {"doctype": "User", "email": "_b33_pilot@example.com", "first_name": "Pilot", "send_welcome_email": 0, "roles": [{"role": "Accounts User"}]}
        ).insert(ignore_permissions=True)
        st = daily_pilot_check()
        self.assertEqual(st["days_left"], 0)
        self.assertFalse(frappe.db.get_value("User", u.name, "enabled"))
        # a recorded subscription ends the pilot logic
        set_tier("Team", subscription_until=add_days(today(), 300), pilot_until=add_days(today(), -31))
        self.assertFalse(daily_pilot_check()["pilot"])


class TestDemoSeedCompany(IntegrationTestCase):
    def test_the_seed_gives_a_company_with_a_tin_its_date_of_incorporation_first(self):
        """A restart re-runs the seed on a company that already has its TIN; since #54 the
        Company refuses to save without a date of incorporation, so the seed sets it first."""
        from unittest.mock import patch

        from ph_cas import demo

        frappe.set_user("Administrator")
        company = frappe.get_all("Company", pluck="name")[0]
        before = frappe.db.get_value("Company", company, ["tax_id", "ph_incorporation_date"], as_dict=True)
        seen = {}

        class Stop(Exception):
            pass

        def fake_setup(name):
            seen["date"] = frappe.db.get_value("Company", name, "ph_incorporation_date")
            raise Stop

        try:
            frappe.db.set_value("Company", company, {"tax_id": "000-111-222", "ph_incorporation_date": None}, update_modified=False)
            with patch("ph_cas.setup.chart.setup_philippine_company", fake_setup):
                with self.assertRaises(Stop):
                    demo.seed()
            self.assertTrue(seen["date"])
        finally:
            frappe.db.set_value("Company", company, {"tax_id": before.tax_id, "ph_incorporation_date": before.ph_incorporation_date}, update_modified=False)


class TestDemoSeedInvoice(IntegrationTestCase):
    def test_the_demo_invoice_carries_a_manual_invoice_number(self):
        """A fresh site's demo seed submits an invoice; since the RDO answer 2 every invoice needs
        a manual number at submit, so the seed must give one (the staging seed failed without it)."""
        import inspect

        from ph_cas import demo

        self.assertIn('"ph_manual_invoice_no": "DEMO-0001"', inspect.getsource(demo.seed))
