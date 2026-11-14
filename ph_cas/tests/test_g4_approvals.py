"""G4: approval chains. A chain with any number of steps (role, user, group or dynamic
recipients; sequential, any one or everyone; approver or notify-only; conditions
that branch by amount) gates Submit; the last approval posts the document; a
rejection returns it to the maker; a change voids the request; the change request
on a filed PH Tax Return opens its amendment. Nothing is on by default."""

import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from ph_cas.approvals import chains, requests
from ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued import generate_quarter
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.fixtures import ensure_service_item, ensure_supplier_profile, ensure_user, make_journal_entry, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY

MAKER = "approval.maker@example.com"
BOSS = "approval.boss@example.com"
BOSS2 = "approval.boss2@example.com"
KEEPER = "approval.keeper@example.com"


def chain(doctype, steps, applies_when="", company=None, title="Test chain"):
    doc = frappe.get_doc({"doctype": "PH Approval Chain", "title": title, "document_type": doctype, "company": company, "enabled": 1, "applies_when": applies_when, "steps": steps})
    doc.flags.ignore_permissions = True
    return doc.insert()


def step(n, title, **kw):
    row = {"step": n, "title": title, "recipient_type": "User", "receiving_order": "Any one", "role_type": "Approver"}
    row.update(kw)
    return row


class TestG4Approvals(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        ensure_user(MAKER, ["Accounts User"])
        ensure_user(BOSS, ["Accounts Manager", "Accounts User"])
        ensure_user(BOSS2, ["Accounts Manager", "Accounts User"])
        ensure_user(KEEPER, ["Accounts User"])
        if not frappe.db.exists("PH Approval Group", "_Test Approvers"):
            frappe.get_doc({"doctype": "PH Approval Group", "group_name": "_Test Approvers", "users": [{"user": BOSS}, {"user": BOSS2}]}).insert(ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 1)
        for n in frappe.get_all("PH Approval Chain", pluck="name"):
            frappe.delete_doc("PH Approval Chain", n, force=True, ignore_permissions=True)
        frappe.db.sql("delete from `tabPH Approval Decision`")
        frappe.db.sql("delete from `tabPH Approval Request`")
        frappe.flags.ph_approval_submit = None

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 0)

    def _je(self, amount):
        frappe.set_user(MAKER)
        je = make_journal_entry(submit=False, amount=amount)
        return je

    def test_nothing_on_by_default_and_the_module_switch(self):
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 0)
        chain("Journal Entry", [step(1, "Boss", user=BOSS)])
        je = self._je(60000)
        self.assertIsNone(chains.chain_for(je))
        je.submit()
        self.assertEqual(je.docstatus, 1)
        frappe.set_user("Administrator")
        frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 1)
        je2 = self._je(60000)
        self.assertIsNotNone(chains.chain_for(je2))
        self.assertFalse(chains.single_user_site())

    def test_manager_above_an_amount_posts_on_approval(self):
        chain("Journal Entry", [step(1, "Accounts manager", recipient_type="Role", role="Accounts Manager")], applies_when="doc.total_debit > 50000", title="Manager above 50,000")
        small = self._je(1000)
        small.submit()
        self.assertEqual(small.docstatus, 1)
        je = self._je(60000)
        with self.assertRaises(frappe.ValidationError) as cm:
            je.submit()
        self.assertIn("Request approval", str(cm.exception))
        je.reload()
        name = requests.open_request("Journal Entry", je.name)
        with self.assertRaises(frappe.ValidationError):
            requests.open_request("Journal Entry", je.name)
        st = requests.status_for("Journal Entry", je.name)
        self.assertTrue(st["applies"])
        self.assertEqual(st["request"]["status"], "Pending")
        self.assertFalse(st["request"]["can_decide"])
        self.assertTrue(st["request"]["can_withdraw"])
        with self.assertRaises(frappe.ValidationError):
            requests.decide(name, "Approved")
        frappe.set_user(BOSS)
        self.assertIn(je.name, [r["document_name"] for r in requests.pending_for()])
        self.assertTrue(requests.status_for("Journal Entry", je.name)["request"]["can_decide"])
        out = requests.decide(name, "Approved", "ok")
        self.assertEqual(frappe.db.get_value("Journal Entry", je.name, "docstatus"), 1)
        self.assertEqual(frappe.db.get_value("PH Approval Request", name, "status"), "Consumed")
        self.assertEqual(out["status"], "Consumed")
        events = frappe.get_all("PH Event Log", {"ref_doctype": "Journal Entry", "ref_name": je.name}, pluck="event")
        for ev in ("approval_requested", "approval_approved", "approval_completed", "submit"):
            self.assertIn(ev, events)
        self.assertNotIn(je.name, [r["document_name"] for r in requests.pending_for()])

    def test_sequential_everyone_any_one_notify_and_branching(self):
        chain(
            "Journal Entry",
            [
                step(1, "Small: boss alone", user=BOSS, condition="doc.total_debit <= 50000"),
                step(2, "Large: both in turn", recipient_type="Group", group="_Test Approvers", receiving_order="Sequential", condition="doc.total_debit > 50000"),
                step(3, "Large: everyone", recipient_type="Group", group="_Test Approvers", receiving_order="Everyone", condition="doc.total_debit > 50000"),
                step(4, "Record keeper", user=KEEPER, role_type="Notify"),
            ],
        )
        je = self._je(1000)
        name = requests.open_request("Journal Entry", je.name)
        req = frappe.get_doc("PH Approval Request", name)
        self.assertEqual([(d.step, d.recipient, d.decision) for d in req.decisions], [(1, BOSS, "Pending")])
        frappe.set_user(BOSS)
        requests.decide(name, "Approved")
        req.reload()
        self.assertEqual(req.status, "Consumed")
        self.assertEqual([(d.step, d.decision) for d in req.decisions], [(1, "Approved"), (4, "Notified")])
        big = self._je(70000)
        name = requests.open_request("Journal Entry", big.name)
        req = frappe.get_doc("PH Approval Request", name)
        self.assertEqual(req.current_step, 2)
        self.assertEqual([(d.recipient, d.decision) for d in req.decisions], [(BOSS, "Pending"), (BOSS2, "Waiting")])
        frappe.set_user(BOSS2)
        with self.assertRaises(frappe.ValidationError):
            requests.decide(name, "Approved")
        frappe.set_user(BOSS)
        requests.decide(name, "Approved")
        req.reload()
        self.assertEqual([(d.recipient, d.decision) for d in req.decisions if d.step == 2], [(BOSS, "Approved"), (BOSS2, "Pending")])
        frappe.set_user(BOSS2)
        requests.decide(name, "Approved")
        req.reload()
        self.assertEqual(req.current_step, 3)
        self.assertEqual({(d.recipient, d.decision) for d in req.decisions if d.step == 3}, {(BOSS, "Pending"), (BOSS2, "Pending")})
        requests.decide(name, "Approved")
        req.reload()
        self.assertEqual(req.status, "Pending")
        frappe.set_user(BOSS)
        requests.decide(name, "Approved")
        req.reload()
        self.assertEqual(req.status, "Consumed")
        self.assertEqual(frappe.db.get_value("Journal Entry", big.name, "docstatus"), 1)
        self.assertIn((4, KEEPER, "Notified"), [(d.step, d.recipient, d.decision) for d in req.decisions])
        # any one: the other recipient is skipped
        frappe.set_user("Administrator")
        for n in frappe.get_all("PH Approval Chain", pluck="name"):
            frappe.delete_doc("PH Approval Chain", n, force=True, ignore_permissions=True)
        chain("Journal Entry", [step(1, "Either boss", recipient_type="Group", group="_Test Approvers", receiving_order="Any one")])
        je = self._je(3000)
        name = requests.open_request("Journal Entry", je.name)
        frappe.set_user(BOSS2)
        requests.decide(name, "Approved")
        req = frappe.get_doc("PH Approval Request", name)
        self.assertEqual({(d.recipient, d.decision) for d in req.decisions}, {(BOSS, "Skipped"), (BOSS2, "Approved")})
        self.assertEqual(frappe.db.get_value("Journal Entry", je.name, "docstatus"), 1)

    def test_reject_withdraw_change_voids_and_self_approval(self):
        chain("Journal Entry", [step(1, "Boss", user=BOSS)])
        je = self._je(5000)
        name = requests.open_request("Journal Entry", je.name)
        frappe.set_user(BOSS)
        with self.assertRaises(frappe.ValidationError):
            requests.decide(name, "Rejected", "")
        requests.decide(name, "Rejected", "wrong account")
        self.assertEqual(frappe.db.get_value("PH Approval Request", name, "status"), "Rejected")
        self.assertEqual(frappe.db.get_value("Journal Entry", je.name, "docstatus"), 0)
        frappe.set_user(MAKER)
        name2 = requests.open_request("Journal Entry", je.name)
        requests.withdraw(name2)
        self.assertEqual(frappe.db.get_value("PH Approval Request", name2, "status"), "Withdrawn")
        name3 = requests.open_request("Journal Entry", je.name)
        je.reload()
        je.user_remark = "changed after the request"
        je.save()
        self.assertEqual(frappe.db.get_value("PH Approval Request", name3, "status"), "Void")
        self.assertIsNone(requests.latest("Journal Entry", je.name))
        with self.assertRaises(frappe.ValidationError):
            je.submit()
        # the requestor is the only recipient: skipped, so the chain passes at once and posts
        frappe.set_user("Administrator")
        for n in frappe.get_all("PH Approval Chain", pluck="name"):
            frappe.delete_doc("PH Approval Chain", n, force=True, ignore_permissions=True)
        chain("Journal Entry", [step(1, "Maker approves themself", user=MAKER)])
        frappe.set_user(MAKER)
        je2 = self._je(5000)
        requests.open_request("Journal Entry", je2.name)
        self.assertEqual(frappe.db.get_value("Journal Entry", je2.name, "docstatus"), 1)
        frappe.set_user("Administrator")
        for n in frappe.get_all("PH Approval Chain", pluck="name"):
            frappe.delete_doc("PH Approval Chain", n, force=True, ignore_permissions=True)
        chain("Journal Entry", [step(1, "Maker may decide", user=MAKER, allow_self_approval=1)])
        frappe.set_user(MAKER)
        je3 = self._je(5000)
        name4 = requests.open_request("Journal Entry", je3.name)
        self.assertTrue(requests.status_for("Journal Entry", je3.name)["request"]["can_decide"])
        requests.decide(name4, "Approved")
        self.assertEqual(frappe.db.get_value("Journal Entry", je3.name, "docstatus"), 1)

    def test_dynamic_lookup_and_templates(self):
        frappe.set_user("Administrator")
        if not frappe.db.exists("PH Approval Lookup", {"document_type": "Journal Entry", "field": "company", "value": TEST_COMPANY}):
            frappe.get_doc({"doctype": "PH Approval Lookup", "document_type": "Journal Entry", "field": "company", "value": TEST_COMPANY, "approver": BOSS2}).insert()
        chain("Journal Entry", [step(1, "Company's approver", recipient_type="Dynamic", dynamic_field="company", use_lookup=1)])
        je = self._je(5000)
        self.assertEqual(chains.recipients(frappe._dict(chains.snapshot(chains.chain_for(je))[0]), je), [BOSS2])
        frappe.set_user("Administrator")
        t = chains.from_template("supervisor_then_manager", "Purchase Order")
        self.assertEqual((t.enabled, len(t.steps), t.steps[1].condition), (0, 2, "doc.grand_total > 50000"))
        self.assertIn("manager_above_amount", chains.TEMPLATES)

    def test_a_filed_tax_return_changes_through_the_chain(self):
        from ph_cas.tests.test_f1_2551q import TAXPAYER

        frappe.set_user("Administrator")
        saved = {k: frappe.db.get_value("Company", TEST_COMPANY, k) for k in TAXPAYER}
        frappe.db.set_value("Company", TEST_COMPANY, TAXPAYER, update_modified=False)
        frappe.clear_document_cache("Company", TEST_COMPANY)
        frappe.clear_cache(doctype="Company")
        self.addCleanup(lambda: (frappe.set_user("Administrator"), frappe.db.set_value("Company", TEST_COMPANY, saved, update_modified=False), frappe.clear_document_cache("Company", TEST_COMPANY), frappe.clear_cache(doctype="Company")))
        sup = ensure_supplier_profile("_Test PH Contractor", ph_vat_status="Non-VAT", ph_payee_type="Non-individual", ph_ewt_category="contractor")
        frappe.db.set_value("Supplier", sup, {"tax_id": "987-654-321", "ph_registered_name": "INVENTED CONTRACTOR CORP"}, update_modified=False)
        frappe.clear_document_cache("Supplier", sup)
        make_purchase_invoice(sup, [(ensure_service_item(), 1, 10000, {})], submit=True)
        qs, _qe = quarter_bounds(today())
        for n in generate_quarter(TEST_COMPANY, str(qs)):
            cert = frappe.get_doc("PH 2307 Issued", n)
            if cert.docstatus == 0:
                cert.submit()
        q = f"{qs.year}-Q{(qs.month - 1) // 3 + 1}"
        for n in frappe.get_all("PH Tax Return", {"company": TEST_COMPANY, "form": "2307"}, pluck="name"):
            frappe.db.sql("delete from `tabPH Tax Return Line` where parent = %s", n)
            frappe.db.sql("delete from `tabPH Tax Return` where name = %s", n)
        chain("PH Tax Return", [step(1, "Accounts manager", recipient_type="Role", role="Accounts Manager")], title="Change to a filed return")
        run = frappe.get_doc({"doctype": "PH Tax Return", "company": TEST_COMPANY, "form": "2307", "period_key": q}).insert()
        run.refresh_from_books()
        run.reload()
        self.assertFalse(requests.status_for("PH Tax Return", run.name)["applies"])
        run.submit()  # filing is not gated by the chain
        run.reload()
        self.assertEqual(run.docstatus, 1)
        frappe.set_user(MAKER)
        with self.assertRaises(frappe.ValidationError):
            run.open_amendment("maker tries alone")
        with self.assertRaises(frappe.ValidationError):
            requests.open_request("PH Tax Return", run.name, "")
        name = requests.open_request("PH Tax Return", run.name, "wrong certificate amounts")
        frappe.set_user(BOSS)
        requests.decide(name, "Approved")
        amend = frappe.db.get_value("PH Tax Return", {"amends": run.name, "docstatus": 0}, "name")
        self.assertTrue(amend)
        self.assertEqual(frappe.db.get_value("PH Approval Request", name, "status"), "Consumed")
        self.assertIn("wrong certificate amounts", frappe.db.get_value("PH Tax Return", amend, "notes"))
        self.assertIn("tax_return.amendment_opened", frappe.get_all("PH Event Log", {"ref_doctype": "PH Tax Return", "ref_name": run.name}, pluck="event"))
