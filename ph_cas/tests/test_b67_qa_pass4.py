"""B67 (QA pass 4): fixes found by the full staging pass, and the pass itself on the parts that
need no history: company setup for the four taxpayer types, and the sales cycle."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from ph_cas.qa import fullpass


class TestB67QAPass4(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_item_tax_template_rows_are_not_added(self):
        # the engine books VAT itself; ERPNext's own copy added zero Output VAT and Input VAT rows
        self.assertEqual(frappe.db.get_single_value("Accounts Settings", "add_taxes_from_item_tax_template"), 0)
        from ph_cas.controls.locks import PHLockError

        s = frappe.get_doc("Accounts Settings")
        s.add_taxes_from_item_tax_template = 1
        with self.assertRaises(PHLockError):
            s.save()

    def test_audit_trail_date_means_the_whole_day(self):
        from ph_cas.ph_cas.report.bir_audit_trail.bir_audit_trail import execute

        frappe.get_doc({"doctype": "ToDo", "description": "B67 audit trail"}).insert()
        _cols, rows = execute({"from_date": today(), "to_date": today(), "sources": "Version"})[:2]
        self.assertTrue(rows)

    def test_companies_and_sales_sections_pass(self):
        for section in ("companies", "purchasing", "sales"):
            res = fullpass.run(section)
            failed = [f"{s['step']}: {s['detail']}" for s in res["steps"] if not s["ok"]]
            self.assertFalse(failed, f"{section}: {failed}")
            for co in fullpass.COMPANIES:
                if frappe.get_cached_value("Company", co, "ph_vat_status") != "VAT":
                    for n in frappe.get_all("Sales Invoice", filters={"company": co, "docstatus": 1}, pluck="name"):
                        heads = [t.account_head for t in frappe.get_doc("Sales Invoice", n).taxes]
                        self.assertFalse([h for h in heads if "VAT" in h], f"{n}: {heads}")


class TestB67Draft2307(IntegrationTestCase):
    def test_draft_certificate_follows_the_bills(self):
        from frappe.utils import add_days

        from ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued import generate_quarter
        from ph_cas.tax.returns import quarter_bounds

        frappe.set_user("Administrator")
        fullpass.run("companies")
        co = fullpass.VAT_CORP
        _sg, s_prof, *_ = fullpass._parties()
        svc = fullpass.item("QA4 Legal Retainer")
        qs, _qe = quarter_bounds(today())
        for d in frappe.get_all("PH 2307 Issued", filters={"company": co, "supplier": s_prof, "docstatus": 0}, pluck="name"):
            frappe.delete_doc("PH 2307 Issued", d)
        fullpass.purchase_invoice(co, s_prof, [(svc, 1, 10000)])
        names = generate_quarter(co, str(qs))
        name = next(n for n in names if frappe.db.get_value("PH 2307 Issued", n, "supplier") == s_prof)
        before = frappe.db.get_value("PH 2307 Issued", name, "total_tax")
        fullpass.purchase_invoice(co, s_prof, [(svc, 1, 20000)])
        self.assertIn(name, generate_quarter(co, str(qs)))
        self.assertEqual(frappe.db.get_value("PH 2307 Issued", name, "total_tax"), before + 1000)


class TestB67ReturnFirst(IntegrationTestCase):
    def test_slsp_and_calendar_read_the_2550q_return(self):
        from ph_cas.dat.relief import _input_vat_on_exempt
        from ph_cas.ph_cas.doctype.ph_tax_return.ph_tax_return import new_return
        from ph_cas.tax.calendar import calendar
        from ph_cas.tax.returns import quarter_bounds

        frappe.set_user("Administrator")
        for section in ("companies", "purchasing", "sales"):
            fullpass.run(section)
        co = fullpass.VAT_CORP
        qs, qe = quarter_bounds(today())
        q = (qs.month - 1) // 3 + 1
        name = new_return(co, "2550Q", f"{qs.year}-Q{q}")
        doc = frappe.get_doc("PH Tax Return", name)
        doc.refresh_from_books()
        line = frappe.db.get_value("PH Tax Return Line", {"parenttype": "PH Tax Return", "parent": name, "item": "53"}, "amount")
        self.assertIsNotNone(line)
        self.assertEqual(_input_vat_on_exempt(co, qs, qe), line)
        row = next(r for r in calendar(co, qs.year) if r["form"] == "2550Q" and r["period_label"] == f"{qs.year}-Q{q}")
        self.assertEqual(row["figures"], name)
        self.assertNotIn("nothing computed", row["status"])
