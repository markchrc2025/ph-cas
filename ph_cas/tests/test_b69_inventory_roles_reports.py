"""B69 (QA pass 4, owner's answers of 17 Nov 2026): the inventory method per company (periodic with
the year-end adjustment, or perpetual), the Owner, Bookkeeper and Cashier role sets, walk-in buyers
on one Generic Customer row of the SLSP, and the report tie-outs."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import get_first_day, get_last_day, today

from ph_cas.controls.locks import PHLockError
from ph_cas.qa import fullpass


def passed(section):
    res = fullpass.run(section)
    return [f"{s['step']}: {s['detail']}" for s in res["steps"] if not s["ok"]]


class TestB69(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_inventory_methods(self):
        self.assertFalse(passed("companies"))
        self.assertFalse(passed("inventory_tracking"))  # periodic year-end (cost of sales = 1702-RT item 30) and perpetual

    def test_roles(self):
        for section in ("companies", "purchasing", "roles"):
            self.assertFalse(passed(section), section)
        from ph_cas.setup import roles

        roles.setup()  # idempotent, and leaves no locked record behind
        roles.setup()
        self.assertTrue(frappe.db.exists("Role Profile", roles.CASHIER))

    def test_walk_in_buyers_on_one_generic_row(self):
        from ph_cas.dat.relief import GENERIC_NAME, GENERIC_TIN, build_sales

        self.assertFalse(passed("companies"))
        walk_in = fullpass.customer("QA4 Walk-in", customer_type="Individual", ph_vat_status="Non-VAT")
        other = fullpass.customer("QA4 Walk-in 2", customer_type="Individual", ph_vat_status="Non-VAT")
        svc = fullpass.item("QA4 Repair Service")
        fullpass.sales_invoice(fullpass.VAT_CO, walk_in, [(svc, 1, 1000)])
        fullpass.sales_invoice(fullpass.VAT_CO, other, [(svc, 1, 500)])
        _n, content, _rows = build_sales(fullpass.VAT_CO, str(get_first_day(today())), str(get_last_day(today())))
        lines = [ln for ln in content.decode().splitlines() if GENERIC_TIN in ln]
        self.assertEqual(len(lines), 1)
        self.assertIn(GENERIC_NAME, lines[0])
        self.assertIn("MARIKINA CITY 1800", lines[0])

    def test_periodic_company_cannot_switch_after_stock(self):
        self.assertFalse(passed("companies"))
        self.assertFalse(passed("inventory_tracking"))
        c = frappe.get_doc("Company", fullpass.PERIODIC_CO)
        c.ph_inventory_method = "Perpetual"
        with self.assertRaises(PHLockError):
            c.save()
