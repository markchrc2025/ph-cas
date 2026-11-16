"""B65 (LDG-57): every demo signup is followed up within 24 hours. Until the Sentire Helpdesk
takes the leads, the owner gets the lead mail (reply goes to the lead), marks it contacted
from a signed link, and is reminded once after 20 hours."""

import csv
import os

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from ph_cas.hosting import demo_access
from ph_cas.hosting.demo_access import contacted_link, mark_contacted, remind_uncontacted_leads, request_access


class TestB65DemoLeads(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.conf.ph_demo_site = 1
        frappe.flags.mute_emails = True
        for p in (demo_access._log_path(), demo_access._followup_path()):
            if os.path.exists(p):
                os.remove(p)

    def tearDown(self):
        frappe.conf.pop("ph_demo_site", None)
        frappe.conf.pop("demo_leads_owner", None)
        frappe.flags.mute_emails = False
        for p in (demo_access._log_path(), demo_access._followup_path()):
            if os.path.exists(p):
                os.remove(p)
        for u in frappe.get_all("User", filters={"name": ["like", "_b65_%"]}, pluck="name"):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _followup(self):
        with open(demo_access._followup_path(), newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_signup_is_listed_marked_contacted_and_reminded_once(self):
        request_access("Lea Ramos", "_b65_lea@example.com", company="Ramos Trading")
        rows = self._followup()
        self.assertEqual([r["email"] for r in rows], ["_b65_lea@example.com"])
        self.assertEqual(rows[0]["contacted_on"], "")

        # 20 hours later, not yet contacted: one reminder, never two
        rows[0]["requested_on"] = str(add_to_date(now_datetime(), hours=-21))[:19]
        demo_access._write_followup({rows[0]["lead"]: rows[0]})
        self.assertEqual(remind_uncontacted_leads(), 1)
        self.assertEqual(remind_uncontacted_leads(), 0)
        self.assertTrue(self._followup()[0]["reminded_on"])

        # the signed link marks it contacted; a forged one is refused
        from urllib.parse import parse_qs, urlparse

        q = parse_qs(urlparse(contacted_link(self._followup()[0])).query)
        lead, sig = q["lead"][0], q["sig"][0]
        with self.assertRaises(frappe.PermissionError):
            mark_contacted(lead, "0" * 32)
        mark_contacted(lead, sig)
        self.assertTrue(self._followup()[0]["contacted_on"])

    def test_owner_is_the_configured_address(self):
        frappe.conf.demo_leads_owner = "owner@firm.ph"
        self.assertEqual(demo_access.lead_owner(), "owner@firm.ph")
