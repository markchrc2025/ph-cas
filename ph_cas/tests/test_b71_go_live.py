"""B71 (after ECOUNT's starting balance): go-live date, opening entries on the cut-over day without a
back-date reason, opening invoices refused, the opening stock count, old balances collected against
the opening entry, and the go-live checklist."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.qa import fullpass


class TestB71GoLive(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_go_live_section(self):
        for section in ("companies", "go_live"):
            res = fullpass.run(section)
            failed = [f"{s['step']}: {s['detail']}" for s in res["steps"] if not s["ok"]]
            self.assertFalse(failed, f"{section}: {failed}")

    def test_ordinary_entries_keep_the_rules(self):
        from frappe.utils import add_days, today

        from ph_cas.controls.locks import PHLockError

        self.assertFalse([s for s in fullpass.run("companies")["steps"] if not s["ok"]])
        co = fullpass.VAT_CORP
        frappe.db.set_value("Company", co, "ph_go_live_date", today())
        frappe.clear_document_cache("Company", co)
        # a non-opening journal entry dated the cut-over day still needs the manager's reason
        je = frappe.get_doc({"doctype": "Journal Entry", "company": co, "posting_date": add_days(today(), -1), "accounts": [
            {"account": fullpass.acc(co, "Cash"), "debit_in_account_currency": 10, "cost_center": fullpass.acc(co, "Main")},
            {"account": fullpass.acc(co, "Capital Stock"), "credit_in_account_currency": 10, "cost_center": fullpass.acc(co, "Main")}]})
        with self.assertRaises(PHLockError):
            je.insert()
