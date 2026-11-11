"""B39: the home page and its single data call."""

import json
import os

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.home import dashboard

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestB39Home(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_page_exists_and_is_the_first_sidebar_item(self):
        self.assertTrue(frappe.db.exists("Page", "sentire-home"))
        items = frappe.get_doc("Sidebar", "Sentire Ledger").items
        first = next(i for i in items if i.type == "Link")
        self.assertEqual((first.link_type, first.link_to), ("Page", "sentire-home"))
        with open(os.path.join(ROOT, "ph_cas", "ph_cas", "page", "sentire_home", "sentire_home.js"), encoding="utf-8") as f:
            self.assertIn("ph_cas.home.dashboard.get", f.read())

    def test_get_returns_every_card_in_one_call(self):
        d = dashboard.get(period="month")
        for key in ("greeting", "first_name", "date", "company", "companies", "period_label", "tiles", "create_actions", "figures", "monthly", "due"):
            self.assertIn(key, d)
        f = d["figures"]
        for key in ("sales", "purchases", "cash", "receivable", "payable", "vat_position", "withholding_to_remit", "drafts"):
            self.assertIn(key, f)
        self.assertEqual(len(d["monthly"]), 12)
        self.assertTrue(json.dumps(d, default=str))

    def test_periods(self):
        from datetime import date

        s, e, label = dashboard.period_bounds("quarter", date(2026, 11, 11))
        self.assertEqual((str(s), str(e), label), ("2026-10-01", "2026-12-31", "Q4 2026"))
        s, e, label = dashboard.period_bounds("last_month", date(2026, 11, 11))
        self.assertEqual((str(s), str(e)), ("2026-10-01", "2026-10-31"))
        self.assertEqual(dashboard.period_bounds("all")[0], None)
        for p in dashboard.PERIODS:
            self.assertIn("period_label", dashboard.get(period=p))

    def test_onboarding_checklist_and_dismiss(self):
        frappe.defaults.clear_user_default("ph_home_hide_onboarding")
        ob = dashboard.get()["onboarding"]
        if ob is not None:
            self.assertEqual(ob["total"], len(ob["steps"]))
            self.assertTrue(all("route" in s for s in ob["steps"]))
        dashboard.hide_onboarding()
        self.assertIsNone(dashboard.get()["onboarding"])
        frappe.defaults.clear_user_default("ph_home_hide_onboarding")

    def test_no_ph_prefix_on_workspace_labels(self):
        ws = frappe.get_doc("Workspace", "Sentire Ledger")
        labels = [s.label for s in ws.shortcuts] + [l.label for l in ws.links if l.type == "Link"]
        self.assertTrue(labels)
        self.assertEqual([l for l in labels if l.startswith("PH ")], [])
        side = [i.label for i in frappe.get_doc("Sidebar", "Sentire Ledger").items]
        self.assertEqual([l for l in side if l.startswith("PH ")], [])
