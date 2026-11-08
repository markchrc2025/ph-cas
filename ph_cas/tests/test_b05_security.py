"""B05: security baseline."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.controls.locks import PHLockError
from ph_cas.controls.security import FORCED_SYSTEM_SETTINGS, _ok, force_system_settings
from ph_cas.tests.fixtures import ensure_user


def _fail_login(user):
    from frappe.auth import add_authentication_log

    add_authentication_log("Incorrect password", user, status="Failed")


class TestB05Security(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_system_settings_are_forced(self):
        settings = frappe.get_doc("System Settings")
        for field, (forced, how) in FORCED_SYSTEM_SETTINGS.items():
            if settings.meta.has_field(field):
                self.assertTrue(_ok(settings.get(field), forced, how), field)

    def test_weakening_a_setting_is_refused(self):
        settings = frappe.get_doc("System Settings")
        settings.deny_multiple_sessions = 0
        with self.assertRaises(PHLockError):
            settings.save()
        settings.reload()
        settings.force_user_to_reset_password = 0
        with self.assertRaises(PHLockError):
            settings.save()
        settings.reload()
        settings.force_user_to_reset_password = 90
        with self.assertRaises(PHLockError):
            settings.save()

    def test_stricter_values_are_allowed(self):
        settings = frappe.get_doc("System Settings")
        settings.force_user_to_reset_password = 14
        settings.flags.ignore_mandatory = True
        settings.save()
        settings.reload()
        self.assertEqual(settings.force_user_to_reset_password, 14)
        force_system_settings()  # does not loosen it back to 30
        self.assertEqual(frappe.db.get_single_value("System Settings", "force_user_to_reset_password"), 14)
        settings.force_user_to_reset_password = 30
        settings.save()

    def test_user_is_deactivated_after_five_failures(self):
        user = ensure_user("ph_lockout@example.com", ["Accounts User"])
        frappe.db.set_value("User", user, "enabled", 1)
        for _ in range(4):
            _fail_login(user)
        self.assertEqual(frappe.db.get_value("User", user, "enabled"), 1)
        _fail_login(user)
        self.assertEqual(frappe.db.get_value("User", user, "enabled"), 0)
        self.assertTrue(
            frappe.db.exists("Comment", {"reference_doctype": "User", "reference_name": user, "comment_type": "Info"})
        )

    def test_failures_count_from_the_last_success(self):
        from frappe.auth import add_authentication_log

        user = ensure_user("ph_lockout2@example.com", ["Accounts User"])
        frappe.db.set_value("User", user, "enabled", 1)
        for _ in range(4):
            _fail_login(user)
        add_authentication_log("Login", user, status="Success")
        for _ in range(4):
            _fail_login(user)
        self.assertEqual(frappe.db.get_value("User", user, "enabled"), 1)

    def test_administrator_is_never_deactivated(self):
        for _ in range(10):
            _fail_login("Administrator")
        self.assertEqual(frappe.db.get_value("User", "Administrator", "enabled"), 1)

    def test_settings_doctype_refuses_the_trademark(self):
        s = frappe.get_doc("PH CAS Settings")
        s.product_name = "ERPNext PH"
        with self.assertRaises(frappe.ValidationError):
            s.save()
        s.reload()
        self.assertEqual(s.failed_signins_before_deactivation, 5)
