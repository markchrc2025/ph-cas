"""B74 (after ECOUNT's customer/supplier ledgers and daily cash report): AR and AP subsidiary ledgers
in the loose-leaf books with the BIR header, tied to the receivable and payable accounts; the daily
cash position tied to the ledger."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.qa import fullpass


class TestB74Ledgers(IntegrationTestCase):
    def test_ledgers_section(self):
        frappe.set_user("Administrator")
        for section in ("companies", "purchasing", "sales", "ledgers"):
            res = fullpass.run(section)
            failed = [f"{s['step']}: {s['detail']}" for s in res["steps"] if not s["ok"]]
            self.assertFalse(failed, f"{section}: {failed}")
