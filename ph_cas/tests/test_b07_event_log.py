"""B07: the hash-chained event log."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.audit.events import GENESIS, compute_hash, record, verify_chain
from ph_cas.tests.fixtures import ensure_user, make_journal_entry, make_sales_invoice


def _rows(**filters):
    return frappe.get_all("PH Event Log", filters=filters, fields=["seq", "event", "ref_doctype", "ref_name", "details", "hash", "previous_hash"], order_by="seq")


class TestB07EventLog(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_chain_starts_at_genesis_and_verifies(self):
        first = frappe.db.get_value("PH Event Log", {"seq": 1}, "previous_hash")
        if first:
            self.assertEqual(first, GENESIS)
        record("test", "Test", "chain")
        result = verify_chain()
        self.assertTrue(result["ok"], result)

    def test_submit_cancel_and_amend_are_recorded(self):
        si = make_sales_invoice()
        events = [r.event for r in _rows(ref_name=si.name)]
        self.assertIn("create", events)
        self.assertIn("submit", events)
        si.cancel()
        self.assertIn("cancel", [r.event for r in _rows(ref_name=si.name)])
        amended = frappe.copy_doc(si)
        amended.amended_from = si.name
        amended.docstatus = 0
        amended.insert()
        amended.submit()
        self.assertIn("amend", [r.event for r in _rows(ref_name=amended.name)])

    def test_print_is_recorded(self):
        si = make_sales_invoice()
        si.run_method("before_print", frappe._dict())
        self.assertIn("print", [r.event for r in _rows(ref_name=si.name)])

    def test_settings_change_is_recorded_with_the_diff(self):
        s = frappe.get_doc("PH CAS Settings")
        s.failed_signins_before_deactivation = 7
        s.save()
        rows = _rows(ref_doctype="PH CAS Settings", event="settings_change")
        self.assertTrue(rows)
        self.assertIn("failed_signins_before_deactivation", rows[-1].details)
        s.failed_signins_before_deactivation = 5
        s.save()

    def test_role_change_and_deactivation_are_recorded(self):
        user = ensure_user("ph_audit_user@example.com", ["Accounts User"])
        u = frappe.get_doc("User", user)
        u.append("roles", {"role": "Accounts Manager"})
        u.save()
        self.assertIn("role_change", [r.event for r in _rows(ref_doctype="User", ref_name=user)])
        u.reload()
        u.enabled = 0
        u.save()
        self.assertIn("user_deactivated", [r.event for r in _rows(ref_doctype="User", ref_name=user)])

    def test_failed_signin_is_recorded(self):
        from frappe.auth import add_authentication_log

        user = ensure_user("ph_audit_fail@example.com", ["Accounts User"])
        add_authentication_log("Incorrect password", user, status="Failed")
        self.assertIn("signin_failed", [r.event for r in _rows(ref_doctype="User", ref_name=user)])

    def test_rows_cannot_be_changed_or_deleted(self):
        row = record("test", "Test", "immutable")
        row.event = "tampered"
        with self.assertRaises(frappe.PermissionError):
            row.save()
        with self.assertRaises(Exception):
            frappe.delete_doc("PH Event Log", row.name, force=True)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc({"doctype": "PH Event Log", "seq": 999999, "event": "forged", "timestamp": frappe.utils.now_datetime(), "user": "x", "previous_hash": GENESIS, "hash": "x"}).insert()

    def test_tampering_breaks_verification(self):
        row = record("test", "Test", "tamper-me", details={"amount": 100})
        frappe.db.savepoint("ph_b07")
        frappe.db.sql("update `tabPH Event Log` set details = %s where name = %s", ('{"amount":1000}', row.name))
        result = verify_chain()
        frappe.db.rollback(save_point="ph_b07")
        self.assertFalse(result["ok"])
        self.assertEqual(result["first_bad_seq"], row.seq)
        self.assertTrue(verify_chain()["ok"])

    def test_hash_is_deterministic(self):
        a = compute_hash(GENESIS, 1, "2026-11-09 00:00:00.000000", "u", "e", "D", "N", 1, "{}")
        b = compute_hash(GENESIS, 1, "2026-11-09 00:00:00.000000", "u", "e", "D", "N", 1, "{}")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_two_thousand_rows_verify_quickly(self):
        import time

        for i in range(2000):
            record("perf", "Test", str(i))
        start = time.time()
        result = verify_chain()
        self.assertTrue(result["ok"])
        self.assertLess(time.time() - start, 10)

    def test_journal_entry_events_are_chained(self):
        je = make_journal_entry()
        rows = _rows(ref_name=je.name)
        self.assertEqual([r.event for r in rows][-2:], ["create", "submit"])
        seqs = [r.seq for r in frappe.get_all("PH Event Log", fields=["seq"], order_by="seq")]
        self.assertEqual(seqs, list(range(1, len(seqs) + 1)))
