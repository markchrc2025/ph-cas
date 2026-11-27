"""B93: the provider's settings are the provider's; the Owner changes the tier."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from ph_cas.hosting import tiers


class TestB93ProviderSettings(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._tier = frappe.db.get_single_value("PH CAS Settings", "subscription_tier") or "Internal"
        self.addCleanup(self._restore)

    def _restore(self):
        frappe.set_user("Administrator")
        tiers.set_tier(self._tier)
        frappe.db.set_single_value("PH CAS Settings", {"scheduled_tier": None, "scheduled_tier_on": None})

    def _owner(self):
        email = "b93.owner@example.test"
        if not frappe.db.exists("User", email):
            u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "B93", "send_welcome_email": 0, "ph_provider_staff": 1})
            u.flags.ignore_permissions = True
            u.insert()
            u.add_roles("System Manager")
        return email

    def test_tenant_owner_cannot_open_or_edit_provider_settings(self):
        frappe.set_user(self._owner())
        self.assertFalse(frappe.has_permission("PH CAS Settings", "read"))
        self.assertFalse(frappe.has_permission("PH CAS Settings", "write"))
        self.assertFalse(frappe.has_permission("PH Subscription", "read"))
        self.assertTrue(frappe.has_permission("PH Security Settings", "write"))

    def test_upgrade_applies_now(self):
        tiers.set_tier("Solo", subscription_until=add_days(today(), 20))
        frappe.set_user(self._owner())
        r = tiers.change_tier("Team")
        self.assertTrue(r["applied"])
        self.assertEqual(tiers.limits()["tier"], "Team")
        self.assertEqual(tiers.limits()["max_users"], 5)

    def test_downgrade_waits_for_the_paid_period_and_cancel(self):
        end = add_days(today(), 20)
        tiers.set_tier("Business", subscription_until=end)
        frappe.set_user(self._owner())
        if tiers._misfits("Team"):
            self.skipTest("the test site is too big for Team")
        r = tiers.change_tier("Team")
        self.assertFalse(r["applied"])
        self.assertEqual(getdate(r["scheduled_tier_on"]), getdate(end))
        self.assertEqual(tiers.limits()["tier"], "Business")
        tiers.apply_scheduled_tier()  # not yet due
        self.assertEqual(tiers.limits()["tier"], "Business")
        frappe.db.set_single_value("PH CAS Settings", "scheduled_tier_on", today())
        frappe.clear_cache()
        tiers.apply_scheduled_tier()
        self.assertEqual(tiers.limits()["tier"], "Team")
        tiers.set_tier("Business", subscription_until=end)
        tiers.change_tier("Team")
        tiers.cancel_downgrade()
        self.assertFalse(frappe.db.get_single_value("PH CAS Settings", "scheduled_tier"))

    def test_downgrade_that_does_not_fit_is_refused_with_what_to_fix(self):
        tiers.set_tier("Business")
        frappe.set_user(self._owner())
        orig = tiers.usage

        def big():
            return {**orig(), "users": 9}

        tiers.usage = big
        try:
            with self.assertRaises(tiers.PHTierError) as e:
                tiers.change_tier("Team")
            self.assertIn("disable 4", str(e.exception))
        finally:
            tiers.usage = orig

    def test_internal_and_enterprise_are_not_self_service(self):
        tiers.set_tier("Internal")
        frappe.set_user(self._owner())
        with self.assertRaises(tiers.PHTierError):
            tiers.change_tier("Team")
        frappe.set_user("Administrator")
        tiers.set_tier("Team")
        frappe.set_user(self._owner())
        with self.assertRaises(tiers.PHTierError):
            tiers.change_tier("Enterprise")
