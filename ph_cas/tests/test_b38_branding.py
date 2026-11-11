"""B38: no Frappe or ERPNext branding anywhere a user looks; the product everywhere."""

import os

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas import branding
from ph_cas.audit.header import platform_version, software_version

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRAMEWORK = ("Frappe", "ERPNext", "frappe.io", "frappeframework.com")


class TestB38Branding(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.flags.mute_emails = True
        self.summary = branding.apply("Sentire Ledger", "MCRC Tax and Accounting Services")

    def tearDown(self):
        frappe.flags.mute_emails = False

    def test_assets_exist(self):
        for key, path in branding.ASSETS.items():
            local = os.path.join(ROOT, "ph_cas", "public", path.replace("/assets/ph_cas/", ""))
            self.assertTrue(os.path.exists(local), f"{key}: {local}")

    def test_settings_carry_the_product_not_the_framework(self):
        self.assertIn("Sentire Ledger", self.summary)
        ws = frappe.get_single("Website Settings")
        self.assertEqual(ws.app_name, "Sentire Ledger")
        self.assertEqual(ws.app_logo, branding.ASSETS["logo"])
        self.assertEqual(ws.favicon, branding.ASSETS["favicon"])
        self.assertEqual(ws.splash_image, branding.ASSETS["logo"])
        self.assertIn("operated by", ws.footer_powered)
        for s in FRAMEWORK:
            self.assertNotIn(s, ws.footer_powered)
        nb = frappe.get_single("Navbar Settings")
        self.assertEqual(nb.app_logo, branding.ASSETS["logo"])
        for row in nb.help_dropdown:
            if row.item_label in branding.HIDDEN_HELP_ITEMS:
                self.assertTrue(row.hidden, row.item_label)
        self.assertEqual(frappe.db.get_single_value("System Settings", "app_name"), "Sentire Ledger")
        self.assertEqual(int(frappe.db.get_default("disable_standard_email_footer") or 0), 1)

    def test_login_page_and_desk_boot_show_the_product(self):
        from frappe.core.doctype.navbar_settings.navbar_settings import get_app_logo

        self.assertEqual(get_app_logo(), branding.ASSETS["logo"])
        bootinfo = frappe._dict(
            app_logo_url="/assets/erpnext/images/erpnext-logo.svg",
            sysdefaults={"app_name": "ERPNext"},
            app_data=[
                {"app_name": "erpnext", "app_title": "ERPNext", "app_logo_url": "/assets/erpnext/images/erpnext-logo.svg"},
                {"app_name": "frappe", "app_title": "Frappe Framework", "app_logo_url": "/assets/frappe/images/x.svg"},
            ],
        )
        branding.boot_session(bootinfo)
        self.assertEqual(bootinfo.app_logo_url, branding.ASSETS["logo"])
        self.assertEqual(bootinfo.sysdefaults["app_name"], "Sentire Ledger")
        self.assertEqual(bootinfo.app_data[0]["app_title"], "Sentire Ledger")
        for app in bootinfo.app_data:
            self.assertEqual(app["app_logo_url"], branding.ASSETS["logo"])
        self.assertEqual(bootinfo.ph_cas_branding["product"], "Sentire Ledger")
        self.assertIn("GPL", bootinfo.ph_cas_branding["licences"])

    def test_emails_carry_the_product_and_no_framework_footer(self):
        from frappe.email.email_body import get_footer, get_formatted_html

        footer = get_footer(None)
        for s in ("Sent via",) + FRAMEWORK:
            self.assertNotIn(s, footer)
        self.assertIn("operated by", footer)
        # the full container needs built assets (CSS inlining), which the CI bench lacks
        if os.path.exists(os.path.join(frappe.local.sites_path, "assets", "assets.json")):
            html = get_formatted_html("Test", "<p>Body</p>", header=["Your demo access", "blue"], with_container=True)
            self.assertIn("Sentire Ledger", html)
            self.assertIn("Your demo access", html)
            for s in ("Sent via", "frappe.io", "ERPNext"):
                self.assertNotIn(s, html)
        from frappe.email.email_body import get_brand_logo, get_brand_name

        self.assertEqual(get_brand_name(), "Sentire Ledger")
        self.assertEqual(get_brand_logo(None), branding.ASSETS["logo"])

    def test_legacy_outgoing_account_is_renamed_to_the_product(self):
        legacy, product = "Outgoing (SMTP)", "Sentire Ledger"
        for n in (legacy, product):
            if frappe.db.exists("Email Account", n):
                frappe.delete_doc("Email Account", n, force=True, ignore_permissions=True)
        doc = frappe.get_doc(
            {
                "doctype": "Email Account",
                "email_account_name": legacy,
                "email_id": "noreply@example.test",
                "smtp_server": "smtp.example.test",
                "enable_outgoing": 1,
                "default_outgoing": 1,
                "no_smtp_authentication": 1,
                "awaiting_password": 0,
            }
        )
        doc.flags.ignore_validate = True
        doc.flags.ignore_permissions = True
        doc.insert()
        try:
            os.environ["SMTP_HOST"] = "smtp.example.test"
            os.environ["SMTP_FROM"] = "noreply@example.test"
            os.environ["SMTP_FROM_NAME"] = product
            from ph_cas.deploy_config import _email_account

            out = _email_account()
            self.assertFalse(frappe.db.exists("Email Account", legacy), out)
            self.assertTrue(frappe.db.exists("Email Account", product), out)
            branding.apply(product, "MCRC")
            acc = frappe.get_doc("Email Account", product)
            self.assertEqual(acc.email_account_name, product)
            self.assertTrue(acc.always_use_account_name_as_sender_name)
            self.assertIn("wordmark.png", acc.brand_logo or "")
        finally:
            for k in ("SMTP_HOST", "SMTP_FROM", "SMTP_FROM_NAME"):
                os.environ.pop(k, None)
            for n in (legacy, product):
                if frappe.db.exists("Email Account", n):
                    frappe.delete_doc("Email Account", n, force=True, ignore_permissions=True)

    def test_prints_show_product_version_only_and_the_pack_shows_the_platform(self):
        for s in FRAMEWORK:
            self.assertNotIn(s, software_version())
        self.assertIn("ERPNext", platform_version())

    def test_new_system_user_lands_on_the_product_workspace(self):
        email = "b38.user@example.test"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "B38", "send_welcome_email": 0, "user_type": "System User"})
        u.flags.ignore_permissions = True
        u.insert()
        try:
            self.assertEqual(frappe.db.get_value("User", email, "default_workspace"), branding.WORKSPACE)
        finally:
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)

    def test_shell_is_first_on_the_rail_and_the_desk_opens_on_it(self):
        from frappe.boot import get_bootinfo
        from frappe.desk.doctype.dock.dock import get_site_dock_layer

        self.assertTrue(frappe.db.exists("Sidebar", branding.SIDEBAR))
        rail = get_site_dock_layer("erpnext")
        self.assertEqual((rail[0]["link_type"], rail[0]["link_to"]), ("Sidebar", branding.SIDEBAR))
        self.assertEqual(frappe.db.get_value("User", "Administrator", "default_workspace"), branding.WORKSPACE)
        boot = get_bootinfo()
        self.assertEqual(boot.home_shell, branding.SIDEBAR)
        erp = [a for a in boot.app_data if a.get("app_name") == "erpnext"]
        self.assertEqual(erp[0]["app_title"] if erp else "Sentire Ledger", "Sentire Ledger")

    def test_framework_onboarding_text_says_the_product(self):
        for name, title in frappe.get_all("Module Onboarding", fields=["name", "title"], as_list=True):
            for s in FRAMEWORK:
                self.assertNotIn(s, title or "", name)
        for name, title in frappe.get_all("Onboarding Step", fields=["name", "title"], as_list=True):
            for s in FRAMEWORK:
                self.assertNotIn(s, title or "", name)

    def test_no_framework_names_in_user_facing_templates_and_website(self):
        offenders = []
        for base in ("ph_cas/www", "ph_cas/templates", "website", "ph_cas/public/js"):
            d = os.path.join(ROOT, base)
            for dirpath, _, files in os.walk(d):
                for f in files:
                    if not f.endswith((".html", ".js", ".md")):
                        continue
                    text = open(os.path.join(dirpath, f), encoding="utf-8").read()
                    for s in ("Powered by ERPNext", "Sent via ERPNext", "Built on Frappe", "frappe.io"):
                        if s in text:
                            offenders.append((f, s))
        self.assertEqual(offenders, [])
