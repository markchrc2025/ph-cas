"""B84 (owner, 21 Nov 2026): issued invoices and collection receipts may be cancelled, by
Staff too; a Cancel approval chain, where set, gates the cancel."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.approvals import chains, requests
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import ensure_user, make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_g4_approvals import chain, step

BOSS = "approval.boss@example.com"


class TestB84Cancel(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        ensure_user(BOSS, ["Accounts Manager", "Accounts User"])

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 1)
        for n in frappe.get_all("PH Approval Chain", pluck="name"):
            frappe.delete_doc("PH Approval Chain", n, force=True, ignore_permissions=True)
        frappe.db.sql("delete from `tabPH Approval Decision`")
        frappe.db.sql("delete from `tabPH Approval Request`")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 0)

    def test_issued_invoice_cancels_without_a_chain(self):
        si = make_sales_invoice()
        si.cancel()
        self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, "docstatus"), 2)

    def test_submit_chain_does_not_gate_cancel(self):
        si = make_sales_invoice()
        chain("Sales Invoice", [step(1, "Boss", user=BOSS)])  # action defaults to Submit
        self.assertIsNone(chains.chain_for(si))
        si.cancel()

    def test_cancel_chain_gates_and_the_approval_cancels(self):
        si = make_sales_invoice()
        c = chain("Sales Invoice", [step(1, "Boss", user=BOSS)], title="Cancel needs the boss")
        frappe.db.set_value("PH Approval Chain", c.name, "action", "Cancel")
        with self.assertRaises(frappe.ValidationError) as e:
            frappe.get_doc("Sales Invoice", si.name).cancel()
        self.assertIn("needs approval to be cancelled", str(e.exception))
        with self.assertRaises(frappe.ValidationError):
            requests.open_request("Sales Invoice", si.name, "")
        req = requests.open_request("Sales Invoice", si.name, "wrong customer")
        frappe.set_user(BOSS)
        requests.decide(req, "Approved", "ok")
        frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, "docstatus"), 2)
        self.assertEqual(frappe.db.get_value("PH Approval Request", req, "status"), "Consumed")
