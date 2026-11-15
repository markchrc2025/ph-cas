"""B52: module toggles (LDG-83), industry presets (LDG-84), module-aware demo and tiers (LDG-85)."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.modules import api
from ph_cas.ph_cas.doctype.ph_subscription.ph_subscription import modules_from_usage

ALWAYS = ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry", "Customer", "Supplier", "Item", "Warehouse", "Company", "PH Tax Return"]


class TestB52Modules(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._reset()

    def tearDown(self):
        self._reset()

    def _reset(self):
        s = frappe.get_doc(api.DOCTYPE)
        for m in api.catalogue():
            s.set(f"module_{m['key']}", 1)
        s.industry = None
        s.configured = 0
        s.flags.ignore_permissions = True
        s.save()
        frappe.db.set_single_value(api.DOCTYPE, "configured", 0)
        frappe.clear_document_cache(api.DOCTYPE, api.DOCTYPE)

    def test_a_site_that_never_chose_has_everything_on(self):
        self.assertTrue(all(api.state().values()))
        h = api.hidden()
        self.assertEqual(h["modules"], [])
        self.assertEqual(h["doctypes"], set())

    def test_switching_stock_off_hides_movements_but_not_the_masters(self):
        api.set_modules(["selling", "buying", "quality"])
        h = api.hidden()
        self.assertIn("stock", h["modules"])
        for dt in ("Stock Entry", "Delivery Note", "Purchase Receipt", "Stock Reconciliation", "Material Request", "Serial No"):
            self.assertIn(dt, h["doctypes"], dt)
        for dt in ALWAYS + ["Item Price", "Price List", "Stock Settings"]:
            self.assertNotIn(dt, h["doctypes"], dt)
        # Quality Inspection lives in Stock but belongs to Quality, which is on
        self.assertNotIn("Quality Inspection", h["doctypes"])
        self.assertIn("Stock Balance", h["reports"])
        self.assertNotIn("Item Prices", h["reports"])
        self.assertIn("Stock", h["sidebars"])

    def test_with_everything_off_only_accounting_and_bir_remain(self):
        api.set_modules([])
        h = api.hidden()
        self.assertEqual(set(h["modules"]), {m["key"] for m in api.catalogue()})
        for dt in ALWAYS:
            self.assertNotIn(dt, h["doctypes"], dt)
        for dt in ("Sales Order", "Quotation", "Purchase Order", "Work Order", "Project", "Asset", "Lead", "Issue", "Quality Inspection", "Maintenance Schedule"):
            self.assertIn(dt, h["doctypes"], dt)
        self.assertIn("Complete Stock Onboarding", h["steps"])
        self.assertIn("Create Opening Stock", h["steps"])  # a step of the Stock guide
        self.assertNotIn("PH Set Up Company", h["steps"])
        self.assertIn("Sales Analytics", set(frappe.get_all("Report", pluck="name")) - h["reports"])

    def test_the_boot_drops_hidden_menus_links_and_search_entries(self):
        api.set_modules(["selling"])
        boot = frappe._dict(
            dock={"erpnext": [{"link_type": "Sidebar", "link_to": "Accounts"}, {"link_type": "Sidebar", "link_to": "Stock"}, {"link_type": "Sidebar", "link_to": "Selling"}]},
            module_sidebars={
                "Stock": {"items": []},
                "Selling": {
                    "items": [
                        {"type": "Link", "link_type": "DocType", "link_to": "Customer"},
                        {"type": "Link", "link_type": "DocType", "link_to": "Delivery Note"},
                        {"type": "Section Break", "label": "Stock things"},
                        {"type": "Link", "link_type": "DocType", "link_to": "Pick List"},
                        {"type": "Section Break", "label": "Setup"},
                        {"type": "Link", "link_type": "DocType", "link_to": "Selling Settings"},
                    ]
                },
            },
            workspaces={"pages": [{"name": "Stock"}, {"name": "Selling"}, {"name": "Accounting"}]},
            user={"can_read": ["Sales Invoice", "Stock Entry", "Item", "Purchase Order"], "can_create": ["Stock Entry", "Customer"]},
        )
        frappe.session.user = "Administrator"
        api.extend_bootinfo(boot)
        self.assertEqual([e["link_to"] for e in boot.dock["erpnext"]], ["Accounts", "Selling"])
        self.assertNotIn("Stock", boot.module_sidebars)
        self.assertEqual(
            [i.get("link_to") or i.get("label") for i in boot.module_sidebars["Selling"]["items"]],
            ["Customer", "Setup", "Selling Settings"],
        )
        self.assertEqual([p["name"] for p in boot.workspaces["pages"]], ["Selling", "Accounting"])
        self.assertEqual(boot.user["can_read"], ["Sales Invoice", "Item"])
        self.assertEqual(boot.user["can_create"], ["Customer"])
        self.assertIn("buying", boot.ph_modules["off"])
        self.assertIn("Purchase Order", boot.ph_modules["doctypes"])

    def test_industry_presets(self):
        state = api.apply_preset("Retail and trading")
        self.assertTrue(state["stock"] and state["selling"] and state["buying"])
        self.assertFalse(state["manufacturing"] or state["projects"])
        self.assertEqual(frappe.db.get_single_value(api.DOCTYPE, "industry"), "Retail and trading")
        self.assertEqual(api.apply_preset("Manufacturing")["manufacturing"], True)
        with self.assertRaises(frappe.ValidationError):
            api.apply_preset("Spaceships")
        for industry, mods in api.presets().items():
            self.assertTrue(set(mods) <= {m["key"] for m in api.catalogue()}, industry)

    def test_the_demo_starts_with_the_common_set_once(self):
        api.apply_demo_set()
        self.assertEqual(sorted(api.modules_on()), ["buying", "selling"])
        api.set_modules(["stock"])
        api.apply_demo_set()  # a choice already made is kept
        self.assertEqual(api.modules_on(), ["stock"])

    def test_the_usage_report_carries_the_modules_for_the_subscription_record(self):
        from ph_cas.hosting.tiers import usage

        api.set_modules(["selling", "crm"])
        self.assertEqual(usage()["modules_on"], ["selling", "crm"])
        self.assertEqual(modules_from_usage('{"modules_on": ["selling", "crm"]}'), "Selling, CRM")
        self.assertEqual(modules_from_usage('{"modules_on": []}'), "None (Accounts and BIR only)")
        self.assertIsNone(modules_from_usage("not json"))

    def test_only_a_system_manager_applies_a_preset(self):
        user = "ph.modules.viewer@example.com"
        if not frappe.db.exists("User", user):
            frappe.get_doc({"doctype": "User", "email": user, "first_name": "Viewer", "roles": [{"role": "Accounts User"}]}).insert(ignore_permissions=True)
        frappe.set_user(user)
        try:
            with self.assertRaises(frappe.PermissionError):
                api.apply_preset("Services")
        finally:
            frappe.set_user("Administrator")
