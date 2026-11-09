"""B32: subscription tiers, limits, usage."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from ph_cas.hosting.tiers import PHTierError, TIERS, check_subscription_status, limits, set_tier, usage
from ph_cas.tests.fixtures import make_sales_invoice


def _user(email, staff=0, enabled=1):
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    return frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": email.split("@")[0],
            "enabled": enabled,
            "user_type": "System User",
            "ph_provider_staff": staff,
            "send_welcome_email": 0,
            "roles": [{"role": "Accounts User"}],
        }
    ).insert(ignore_permissions=True)


class TestB32Tiers(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        set_tier("Internal")

    def tearDown(self):
        set_tier("Internal", subscription_until="", pilot_until="")
        for u in frappe.get_all("User", filters={"name": ["like", "_b32_%"]}, pluck="name"):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_tier_table_matches_the_offer(self):
        self.assertEqual(TIERS["Solo"]["max_users"], 1)
        self.assertEqual(TIERS["Team"], {"max_users": 5, "max_companies": 1, "max_branches": 3, "monthly_invoice_limit": 1000})
        self.assertEqual(TIERS["Business"]["max_branches"], 0)
        self.assertEqual(TIERS["Enterprise"]["max_users"], 0)

    def test_set_tier_writes_limits_and_overrides(self):
        out = set_tier("Team", subscription_until=add_days(today(), 365), max_users=7)
        self.assertEqual(out["max_users"], 7)
        lim = limits()
        self.assertEqual(lim["tier"], "Team")
        self.assertEqual(lim["max_users"], 7)
        self.assertEqual(lim["monthly_invoice_limit"], 1000)
        with self.assertRaises(PHTierError):
            set_tier("Platinum")

    def test_user_limit_counts_seats_but_not_provider_staff(self):
        base = usage()["users"]
        set_tier("Solo", max_users=base + 1)
        _user("_b32_a@example.com")  # fills the last seat
        _user("_b32_staff@example.com", staff=1)  # provider staff never counts
        _user("_b32_off@example.com", enabled=0)  # disabled never counts
        with self.assertRaises(PHTierError):
            _user("_b32_b@example.com")
        # editing an existing seat does not add one
        u = frappe.get_doc("User", "_b32_a@example.com")
        u.first_name = "Renamed"
        u.save(ignore_permissions=True)
        # enabling a disabled user takes a seat
        off = frappe.get_doc("User", "_b32_off@example.com")
        off.enabled = 1
        with self.assertRaises(PHTierError):
            off.save(ignore_permissions=True)

    def test_company_and_branch_limits(self):
        set_tier("Solo")  # 1 company, 1 branch
        with self.assertRaises(PHTierError):
            frappe.get_doc(
                {"doctype": "Company", "company_name": "_B32 Second Co", "abbr": "B32", "default_currency": "PHP", "country": "Philippines"}
            ).insert(ignore_permissions=True)
        if not frappe.db.exists("Branch", "_B32 Main"):
            frappe.get_doc({"doctype": "Branch", "branch": "_B32 Main"}).insert(ignore_permissions=True)
        if frappe.db.count("Branch") >= 1:
            with self.assertRaises(PHTierError):
                frappe.get_doc({"doctype": "Branch", "branch": "_B32 Second"}).insert(ignore_permissions=True)
        set_tier("Business")  # unlimited branches
        frappe.get_doc({"doctype": "Branch", "branch": "_B32 Second"}).insert(ignore_permissions=True)
        frappe.delete_doc("Branch", "_B32 Second", force=True, ignore_permissions=True)
        frappe.delete_doc("Branch", "_B32 Main", force=True, ignore_permissions=True)

    def test_monthly_invoice_limit_counts_submitted_invoices_of_the_month(self):
        n = usage()["invoices_this_month"]
        set_tier("Solo", monthly_invoice_limit=n + 1)
        make_sales_invoice(submit=True)  # the last one allowed this month
        with self.assertRaises(PHTierError):
            make_sales_invoice(submit=True)
        set_tier("Business")
        make_sales_invoice(submit=True)

    def test_usage_and_subscription_status(self):
        u = usage()
        for k in ("tier", "users", "companies", "branches", "invoices_this_month", "max_users"):
            self.assertIn(k, u)
        set_tier("Team", subscription_until=add_days(today(), -1), pilot_until=add_days(today(), -2))
        st = check_subscription_status()
        self.assertTrue(st["expired"])
        self.assertTrue(st["pilot_ended"])
        from ph_cas.ops.monitor import status

        self.assertIn("subscription", status())
