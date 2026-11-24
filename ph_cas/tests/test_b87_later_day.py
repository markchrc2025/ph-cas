"""B87 (LDG-244): a draft bill or invoice approved or submitted on a later day posts today, with
its due dates moved by the same number of days."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from ph_cas.approvals import requests
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import ensure_user, make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_g4_approvals import chain, step

BOSS = "approval.boss@example.com"


def _age(doctype, name, days):
    """Make a saved draft look as if it was saved `days` ago."""
    doc = frappe.get_doc(doctype, name)
    frappe.db.set_value(doctype, name, {"posting_date": add_days(nowdate(), -days), "due_date": add_days(doc.due_date or nowdate(), -days)}, update_modified=False)
    for row in doc.get("payment_schedule") or []:
        frappe.db.set_value(row.doctype, row.name, "due_date", add_days(row.due_date, -days), update_modified=False)


class TestB87LaterDay(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        ensure_user(BOSS, ["Accounts Manager", "Accounts User"])

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 0)

    def test_yesterdays_draft_invoice_submits_today(self):
        si = make_sales_invoice(submit=False)
        due = getdate(si.due_date)
        _age("Sales Invoice", si.name, 1)
        doc = frappe.get_doc("Sales Invoice", si.name)
        doc.submit()
        doc.reload()
        self.assertEqual(getdate(doc.posting_date), getdate(nowdate()))
        self.assertEqual(getdate(doc.due_date), due)

    def test_approval_on_a_later_day_posts(self):
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 1)
        for n in frappe.get_all("PH Approval Chain", pluck="name"):
            frappe.delete_doc("PH Approval Chain", n, force=True, ignore_permissions=True)
        chain("Sales Invoice", [step(1, "Boss", user=BOSS)], title="B87 invoices")
        si = make_sales_invoice(submit=False)
        req = requests.open_request("Sales Invoice", si.name, "")
        _age("Sales Invoice", si.name, 1)
        frappe.set_user(BOSS)
        requests.decide(req, "Approved", "")
        frappe.set_user("Administrator")
        doc = frappe.get_doc("Sales Invoice", si.name)
        self.assertEqual(doc.docstatus, 1)
        self.assertEqual(getdate(doc.posting_date), getdate(nowdate()))
        self.assertGreaterEqual(getdate(doc.due_date), getdate(doc.posting_date))
        for n in frappe.get_all("PH Approval Chain", pluck="name"):
            frappe.delete_doc("PH Approval Chain", n, force=True, ignore_permissions=True)

    def test_dates_are_not_part_of_the_fingerprint(self):
        si = make_sales_invoice(submit=False)
        before = requests.fingerprint(si)
        si.posting_date = add_days(nowdate(), -3)
        si.due_date = add_days(nowdate(), -3)
        self.assertEqual(before, requests.fingerprint(si))
