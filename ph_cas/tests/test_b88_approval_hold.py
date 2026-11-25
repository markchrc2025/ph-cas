"""B88: the boot lists the document types an enabled chain covers, with their actions."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.approvals import chains
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import ensure_user
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_g4_approvals import chain, step

BOSS = "approval.boss@example.com"


class TestB88ApprovalHold(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        ensure_user(BOSS, ["Accounts Manager", "Accounts User"])
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 1)
        for n in frappe.get_all("PH Approval Chain", pluck="name"):
            frappe.delete_doc("PH Approval Chain", n, force=True, ignore_permissions=True)

    def tearDown(self):
        for n in frappe.get_all("PH Approval Chain", pluck="name"):
            frappe.delete_doc("PH Approval Chain", n, force=True, ignore_permissions=True)
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 0)

    def test_boot_lists_covered_doctypes(self):
        chain("Purchase Invoice", [step(1, "Boss", user=BOSS)], title="B88 bills")
        c = chain("Sales Invoice", [step(1, "Boss", user=BOSS)], title="B88 cancels")
        frappe.db.set_value("PH Approval Chain", c.name, "action", "Cancel")
        boot = frappe._dict()
        chains.extend_bootinfo(boot)
        self.assertEqual(boot.ph_cas_chain_doctypes.get("Purchase Invoice"), ["Submit"])
        self.assertEqual(boot.ph_cas_chain_doctypes.get("Sales Invoice"), ["Cancel"])
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 0)
        boot = frappe._dict()
        chains.extend_bootinfo(boot)
        self.assertEqual(boot.ph_cas_chain_doctypes, {})
