"""B37: website pages and the pilot request."""

import csv
import os

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.hosting import demo_access
from ph_cas.hosting.demo_access import request_pilot

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestB37Website(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.flags.mute_emails = True
        p = demo_access._pilot_log_path()
        if os.path.exists(p):
            os.remove(p)

    def tearDown(self):
        frappe.flags.mute_emails = False

    def test_pages_exist_and_carry_no_dashes_or_broken_internal_links(self):
        pages = ["index.html", "pricing.html", "demo.html", "terms.html", "privacy.html", "dpa.html"]
        for n in pages:
            p = os.path.join(ROOT, "website", "ledger", n)
            self.assertTrue(os.path.exists(p), n)
            html = open(p, encoding="utf-8").read()
            self.assertNotIn("—", html, n)
            self.assertNotIn("–", html, n)
            self.assertIn('href="/ledger/assets/site.css"', html)
            self.assertNotIn('href="/assets/', html, n)
            for other in pages:
                if f'href="/ledger/{other}"' in html:
                    self.assertTrue(os.path.exists(os.path.join(ROOT, "website", "ledger", other)))
        front = open(os.path.join(ROOT, "website", "index.html"), encoding="utf-8").read()
        self.assertIn('href="/ledger/"', front)
        self.assertNotIn("—", front)
        pricing = open(os.path.join(ROOT, "website", "ledger", "pricing.html"), encoding="utf-8").read()
        for s in ("Ledger Solo", "Ledger Team", "Ledger Business", "Ledger Enterprise", "1,490", "3,990", "9,990", "24,990"):
            self.assertIn(s, pricing)
        self.assertTrue(os.path.exists(os.path.join(ROOT, "website", "Dockerfile")))

    def test_pilot_request_is_logged_and_validated(self):
        out = request_pilot("Liza Reyes", "_b37_liza@example.com", "Reyes Hardware", mobile="0917", tier="Business", notes="VAT, 2 branches\nusing spreadsheets")
        self.assertTrue(out["ok"])
        rows = list(csv.DictReader(open(demo_access._pilot_log_path(), encoding="utf-8")))
        self.assertEqual(rows[0]["company"], "Reyes Hardware")
        self.assertEqual(rows[0]["tier"], "Business")
        self.assertNotIn("\n", rows[0]["notes"])
        with self.assertRaises(frappe.ValidationError):
            request_pilot("", "bad-email", "X")
        with self.assertRaises(frappe.ValidationError):
            request_pilot("A", "_b37_a@example.com", "")
