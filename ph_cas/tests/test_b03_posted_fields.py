"""B03: nothing posted can be changed or renumbered."""

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.controls.locks import PHLockError
from ph_cas.tests.fixtures import acc, make_sales_invoice


class TestB03PostedFields(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_property_setters_turned_allow_on_submit_off(self):
        meta = frappe.get_meta("Sales Invoice")
        for field in ("cost_center", "project", "write_off_account", "unrealized_profit_loss_account"):
            self.assertFalse(meta.get_field(field).allow_on_submit, field)
        item_meta = frappe.get_meta("Sales Invoice Item")
        for field in ("income_account", "expense_account", "cost_center", "service_stop_date"):
            self.assertFalse(item_meta.get_field(field).allow_on_submit, field)
        self.assertFalse(frappe.get_meta("Payment Entry").get_field("party_name").allow_on_submit)
        self.assertFalse(frappe.get_meta("Sales Taxes and Charges").get_field("account_head").allow_on_submit)
        # presentation fields stay editable
        self.assertTrue(meta.get_field("letter_head").allow_on_submit)

    def test_header_accounting_field_cannot_change_after_submit(self):
        si = make_sales_invoice()
        si.reload()
        other_cc = frappe.get_doc(
            {"doctype": "Cost Center", "cost_center_name": "_Test PH Other CC", "parent_cost_center": acc("_Test PH Company"), "company": si.company, "is_group": 0}
        )
        if not frappe.db.exists("Cost Center", acc("_Test PH Other CC")):
            other_cc.insert()
        si.cost_center = acc("_Test PH Other CC")
        with self.assertRaises(frappe.ValidationError):
            si.save()
        self.assertNotEqual(frappe.db.get_value("Sales Invoice", si.name, "cost_center"), acc("_Test PH Other CC"))

    def test_line_account_cannot_change_after_submit(self):
        si = make_sales_invoice()
        si.reload()
        si.items[0].income_account = acc("Service")
        with self.assertRaises(frappe.ValidationError):
            si.save()

    def test_hook_refuses_even_when_meta_allows(self):
        """Defence in depth: if a field were allow-on-submit, the hook still refuses."""
        si = make_sales_invoice()
        si.reload()
        meta_field = frappe.get_meta("Sales Invoice").get_field("cost_center")
        original = meta_field.allow_on_submit
        meta_field.allow_on_submit = 1
        try:
            si.cost_center = acc("_Test PH Other CC") if frappe.db.exists("Cost Center", acc("_Test PH Other CC")) else acc("Main")
            if si.cost_center == frappe.db.get_value("Sales Invoice", si.name, "cost_center"):
                si.cost_center = None
            with self.assertRaises(PHLockError):
                si.save()
        finally:
            meta_field.allow_on_submit = original

    def test_presentation_field_can_change_after_submit(self):
        si = make_sales_invoice()
        si.reload()
        si.title = "Changed title"
        si.save()
        self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, "title"), "Changed title")

    def test_no_repost_is_ever_created(self):
        before = frappe.db.count("Repost Accounting Ledger")
        si = make_sales_invoice()
        si.reload()
        si.title = "Still no repost"
        si.save()
        try:
            si.items[0].income_account = acc("Service")
            si.save()
        except frappe.ValidationError:
            pass
        self.assertEqual(frappe.db.count("Repost Accounting Ledger"), before)

    def test_amendment_keeps_the_original_cancelled(self):
        si = make_sales_invoice()
        si.cancel()
        amended = frappe.copy_doc(si)
        amended.amended_from = si.name
        amended.docstatus = 0
        amended.insert()
        self.assertEqual(amended.name, f"{si.name}-1")
        self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, "docstatus"), 2)

    def test_series_counter_cannot_be_moved(self):
        settings = frappe.get_doc("Document Naming Settings")
        settings.transaction_type = "Sales Invoice"
        settings.prefix = "ACC-SINV-.YYYY.-"
        settings.current_value = 1
        with self.assertRaises(PHLockError):
            settings.update_series_start()

    def test_series_counter_of_other_doctypes_still_works(self):
        settings = frappe.get_doc("Document Naming Settings")
        settings.transaction_type = "Task"
        settings.prefix = "TASK-"
        row = frappe.db.sql("select current from `tabSeries` where name = %s", "TASK-")
        settings.current_value = int(row[0][0]) if row else 0
        settings.update_series_start()  # no error
