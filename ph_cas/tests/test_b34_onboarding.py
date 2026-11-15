"""B34: Sentire Ledger onboarding module, workspace and video overrides."""

import json

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.setup import onboarding
from ph_cas.setup.onboarding import ONBOARDING, STEPS, WORKSPACE, apply_videos


class TestB34Onboarding(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        onboarding.setup()

    def test_module_onboarding_has_the_six_steps_in_order(self):
        mo = frappe.get_doc("Module Onboarding", ONBOARDING)
        self.assertEqual(mo.title, "Get to know Sentire Ledger")
        self.assertEqual([r.step for r in mo.steps], [s["name"] for s in STEPS])
        for s in STEPS:
            doc = frappe.get_doc("Onboarding Step", s["name"])
            self.assertEqual(doc.title, s["title"])
            self.assertEqual(doc.module_onboarding, ONBOARDING)
            if s["action"] == "Create Entry":
                self.assertTrue(frappe.db.exists("DocType", s["reference_document"]))
            if s["action"] == "View Report":
                self.assertTrue(frappe.db.exists("Report", s["reference_report"]))

    def test_workspace_carries_the_onboarding_and_only_existing_links(self):
        ws = frappe.get_doc("Workspace", WORKSPACE)
        self.assertEqual(ws.module_onboarding, ONBOARDING)
        blocks = json.loads(ws.content)
        self.assertEqual(blocks[0]["type"], "onboarding")
        for l in ws.links:
            if l.type == "Link":
                self.assertTrue(frappe.db.exists(l.link_type, l.link_to), l.link_to)
        for s in ws.shortcuts:
            self.assertTrue(frappe.db.exists(s.type, s.link_to), s.link_to)

    def test_no_card_plays_youtube_and_our_videos_are_mapped(self):
        frappe.db.set_value("Onboarding Step", "Create Customer", "intro_video_url", "https://www.youtube.com/watch?v=ctgyKAvyhJs", update_modified=False)
        out = apply_videos()
        self.assertIn("Create Customer", out["cleared"])
        self.assertEqual(frappe.db.count("Onboarding Step", {"intro_video_url": ["is", "set"]}), 0)
        self.assertEqual(frappe.db.get_value("PH Tutorial Video Step", {"step": "Create Customer"}, "parent"), "V09")

    def test_setup_is_idempotent(self):
        onboarding.setup()
        onboarding.setup()
        self.assertEqual(frappe.db.count("Onboarding Step", {"module_onboarding": ONBOARDING}), len(STEPS))
        self.assertEqual(frappe.db.count("Workspace", {"name": WORKSPACE}), 1)
