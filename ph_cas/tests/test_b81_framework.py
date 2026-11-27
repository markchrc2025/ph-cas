"""B81: Ledger runs on Sentire Framework (Sentire's own framework, based on Frappe).

Checks that the bench was built from Sentire Framework, that users still see Sentire Ledger
and never Frappe, that the BIR documents name the real platform, that the framework makes
no outbound update call, and that the cross-app event format works."""

import re
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas import branding
from ph_cas.audit.header import framework_label, platform_version

# The one place users may read "Frappe": the licences line in About, which the MIT licence requires
LICENCE_ALLOWED = re.compile(r"based on Frappe Framework [\d.]+")


def visible_text(html: str) -> str:
    """Text a person reads: scripts, styles, comments and tags removed."""
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    html = re.sub(r"(?s)<!--.*?-->", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


class TestB81Framework(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.flags.mute_emails = True
        branding.apply("Sentire Ledger", "MCRC Tax and Accounting Services")

    def tearDown(self):
        frappe.flags.mute_emails = False
        frappe.set_user("Administrator")

    def test_bench_is_built_from_sentire_framework(self):
        from frappe import sentire

        self.assertTrue(sentire.release().startswith(f"v{frappe.__version__}-sentire."))
        self.assertEqual(frappe.get_hooks("app_title", app_name="frappe")[0], "Sentire Framework")
        # the version number itself stays upstream's, so ERPNext's frappe>=16 check still passes
        self.assertRegex(frappe.__version__, r"^\d+\.\d+\.\d+$")

    def test_info_api(self):
        info = frappe.call("frappe.sentire.info")
        self.assertEqual(info["name"], "Sentire Framework")
        self.assertEqual(info["based_on"], "Frappe Framework")
        self.assertEqual(info["based_on_version"], frappe.__version__)

    def test_bir_documents_name_the_platform(self):
        label = framework_label()
        self.assertTrue(label.startswith("Sentire Framework v"))
        self.assertIn("based on Frappe Framework", label)
        # B92: the BIR documents name only Sentire Framework
        self.assertTrue(platform_version().endswith(f"({label.split(' (based on')[0]})"))
        self.assertNotIn("ERPNext", platform_version())
        self.assertNotIn("Frappe", platform_version())

    def test_licences_line_credits_frappe_under_mit(self):
        text = branding.licence_text()
        self.assertIn("Sentire Framework", text)
        self.assertIn("based on Frappe Framework", text)
        self.assertIn("(MIT)", text)

    def test_login_page_shows_the_product_not_frappe(self):
        import os

        from frappe.www import login

        from frappe.utils import set_request

        frappe.set_user("Guest")
        try:
            set_request(method="GET", path="/login")
            context = frappe._dict()
            login.get_context(context)
            # the full page needs built assets, which the CI bench skips (same as B38)
            html = None
            if os.path.exists(os.path.join(frappe.local.sites_path, "assets", "assets.json")):
                from frappe.website.serve import get_response_content

                html = get_response_content("login")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(context.app_name, "Sentire Ledger")
        self.assertIn("ph_cas", str(context.logo))
        if html:
            text = visible_text(html)
            self.assertIn("Sentire Ledger", text)
            self.assertNotIn("Frappe", text)
            self.assertNotIn("ERPNext", text)
            self.assertIn('content="sentire-framework"', html)

    def test_page_template_carries_the_sentire_generator(self):
        from frappe import get_app_path

        with open(get_app_path("frappe", "templates", "base.html")) as f:
            base = f.read()
        self.assertIn('content="sentire-framework"', base)
        self.assertNotIn("frappeframework.com", base)

    def test_boot_shows_the_product_not_frappe(self):
        from frappe.boot import get_bootinfo

        boot = get_bootinfo()
        self.assertEqual(boot.sysdefaults.get("app_name"), "Sentire Ledger")
        for app in boot.app_data:
            title = str(app.get("app_title") or "")
            self.assertNotIn("Frappe", title, app)
        licences = str((boot.get("ph_cas_branding") or {}).get("licences") or "")
        self.assertIn("Sentire Framework", licences)
        self.assertNotIn("Frappe", LICENCE_ALLOWED.sub("", licences))

    def test_update_check_makes_no_outbound_call(self):
        """Even with B80's System Settings guard switched off, the framework sends nothing."""
        from frappe.utils import change_log

        before = frappe.db.get_single_value("System Settings", "disable_system_update_notification")
        frappe.db.set_single_value("System Settings", "disable_system_update_notification", 0)
        calls = []

        def refuse(*args, **kwargs):
            calls.append(args)
            raise AssertionError("outbound call attempted")

        try:
            with patch("requests.get", refuse), patch("requests.post", refuse), patch(
                "requests.Session.request", refuse
            ):
                change_log.check_for_update()
                change_log.show_update_popup()
        finally:
            frappe.db.set_single_value("System Settings", "disable_system_update_notification", before)
        self.assertEqual(calls, [])

    def test_product_suggestions_are_off(self):
        from ph_cas.controls import security

        self.assertEqual(security.FORCED_SYSTEM_SETTINGS.get("disable_product_suggestion"), (1, "eq"))

    def test_event_round_trip(self):
        from frappe import sentire

        event = sentire.build_event("ledger.task.created", "ledger", {"task_id": "T1"}, "ACME")
        body = sentire.encode_event(event)
        header = sentire.sign(body, "secret")
        self.assertTrue(sentire.verify(body, header, "secret"))
        self.assertFalse(sentire.verify(body + b" ", header, "secret"))
        self.assertFalse(sentire.verify(body, header, "other"))
