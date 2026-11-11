"""F0: the PH Tax Return record, its needs, its seal and the confirmation basis.
The 2551Q engine is not built yet in F0, so the return reports that as a need and
refuses to be filed; the common layer is what is tested here."""

import json
from datetime import date

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.forms import confirmation as conf
from ph_cas.forms import period as period_mod
from ph_cas.forms.export import enc, file_name, tin_parts, write_lined, write_tabbed
from ph_cas.forms.money import amt, centavos, dec, total, whole_peso
from ph_cas.forms.needs import company_needs
from ph_cas.forms.registry import FORMS, spec


class TestF0Common(IntegrationTestCase):
    def test_money_is_exact_and_rounds_the_bir_way(self):
        self.assertEqual(str(total("0.1", "0.2")), "0.3")
        self.assertEqual(whole_peso("10.49"), 10)
        self.assertEqual(whole_peso("10.50"), 11)
        self.assertEqual(whole_peso("-10.50"), -11)
        self.assertEqual(str(centavos("1234.565")), "1234.57")
        self.assertEqual(amt("1234567.5"), "1,234,567.50")
        self.assertEqual(dec("1,234.50"), dec("1234.5"))
        self.assertEqual(dec("abc"), 0)

    def test_periods_follow_the_calendar_or_the_fiscal_year(self):
        p = period_mod.parse("2026-Q1", "quarter")
        self.assertEqual((p.start, p.end), (date(2026, 1, 1), date(2026, 3, 31)))
        f = period_mod.parse("2026-Q1", "quarter", "2025-07-01")
        self.assertEqual((f.start, f.end, f.fiscal), (date(2025, 7, 1), date(2025, 9, 30), True))
        y = period_mod.parse("2026", "year", "2025-07-01")
        self.assertEqual((y.start, y.end), (date(2025, 7, 1), date(2026, 6, 30)))
        m = period_mod.parse("2026-03", "month", "2025-07-01")
        self.assertEqual((m.start, m.end), (date(2026, 3, 1), date(2026, 3, 31)))
        with self.assertRaises(ValueError):
            period_mod.parse("2026-Q5", "quarter")
        self.assertEqual(period_mod.key_for("quarter", date(2025, 7, 1), "2025-07-01"), "2026-Q1")
        self.assertEqual(period_mod.mdy(date(2026, 1, 1)), "1/01/2026")

    def test_export_writer_matches_the_package_layouts(self):
        rows = [("frm2551Qv2018:txtYear", "2026"), ("txtEmail", "a@b.c")]
        tabbed = write_tabbed(rows)
        self.assertTrue(tabbed.startswith("<?xml version='1.0'?>\t\t<div>frm2551Qv2018:txtYear=2026frm2551Qv2018:txtYear=</div>\t\t<div>"))
        self.assertTrue(tabbed.endswith("\t\t\t\tAll Rights Reserved BIR 2012.0"))
        lined = write_lined(rows)
        self.assertIn("<?xml version='1.0'?>        <div>frm2551Qv2018:txtYear", lined)
        self.assertTrue(lined.endswith("\n        All Rights Reserved BIR 2012.0"))
        self.assertEqual(enc("A B, C"), "A%20B%2C%20C")
        t = tin_parts("123-456-789", "00000")
        self.assertEqual((t["t1"], t["t2"], t["t3"], t["branch3"], t["branch5"]), ("123", "456", "789", "000", "00000"))
        self.assertEqual(file_name("123456789", "00000", "2551Q", "2018", "12", "2026", 3), "1234567890002551Qv2018122026Q3.xml")

    def test_needs_ask_for_what_the_company_lacks(self):
        c = {"name": "X", "tax_id": "", "ph_branch_code": "00000", "ph_taxpayer_type": "Non-individual", "ph_registered_name": "X CORP", "ph_rdo": "", "ph_registered_address": "1 St", "ph_zip": "1234", "ph_contact_number": "", "ph_email": "a@b.c"}
        keys = [n.key for n in company_needs(spec("2551Q"), c)]
        self.assertEqual(keys, ["company.tin", "company.rdo", "company.contact"])
        c.update({"tax_id": "123-456-789", "ph_rdo": "044", "ph_contact_number": "0917"})
        self.assertEqual(company_needs(spec("2551Q"), c), [])
        c["ph_taxpayer_type"] = "Individual"
        keys = [n.key for n in company_needs(spec("1701Q"), c)]
        self.assertEqual(keys, ["company.name", "company.civil_status", "company.birthdate", "company.citizenship"])

    def test_confirmation_file_names_and_text_are_read(self):
        p = conf.parse_file_name("111222333000-2550Qv2024-122026Q1.xml")
        self.assertEqual((p.form, p.tin, p.branch, p.tax_year, p.quarter, p.fy_end_month), ("2550Q", "111222333", 0, 2026, 1, 12))
        p = conf.parse_file_name("11122233300000-0619E-072026V1.xml")
        self.assertEqual((p.form, p.month, p.tax_year, p.amendment), ("0619E", 7, 2026, 1))
        self.assertIsNone(conf.parse_file_name("nothing.xml"))
        text = (
            "From: eBIRForms <ebirforms-noreply@bir.gov.ph>\nSubject: Tax Return Receipt Confirmation\n\n"
            "This confirms receipt of your submission with the following details:\nFile name: 11122233300000-1601EQ-2026Q3.xml\n"
            "Date received by BIR: 25 October 2026\nTime received by BIR: 11:40 AM\n"
        )
        facts = conf.read_confirmation(text.encode(), "mail.txt")
        self.assertTrue(facts.from_bir)
        self.assertEqual(facts.file_name, "11122233300000-1601EQ-2026Q3.xml")
        self.assertEqual(facts.received_at.strftime("%Y-%m-%d %H:%M"), "2026-10-25 11:40")
        self.assertEqual(conf.check_against(facts, "1601EQ", "111-222-333", "00000", "quarter", 2026, 3), [])
        errs = conf.check_against(facts, "2551Q", "111-222-333", "00000", "quarter", 2026, 2)
        self.assertEqual(len(errs), 2)

    def test_registry_covers_the_milestone(self):
        for code in ("2551Q", "2550Q", "0619-E", "1601-EQ", "1600-VT", "1701Q", "1701", "1701A", "1702Q", "1702-RT", "1604-E", "2307"):
            self.assertIn(code, FORMS)


class TestF0TaxReturn(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.company = frappe.get_all("Company", pluck="name", limit=1)[0]
        for n in frappe.get_all("PH Tax Return", {"company": self.company, "form": "2551Q", "period_key": "2026-Q1", "docstatus": 0}, pluck="name"):
            frappe.delete_doc("PH Tax Return", n, force=True, ignore_permissions=True)

    def test_a_return_knows_its_period_and_its_needs_and_refuses_to_file_unbuilt(self):
        doc = frappe.get_doc({"doctype": "PH Tax Return", "company": self.company, "form": "2551Q", "period_key": "2026-q1"})
        doc.insert()
        self.assertEqual(doc.period_key, "2026-Q1")
        self.assertEqual(str(doc.period_start), "2026-01-01")
        self.assertEqual(str(doc.period_end), "2026-03-31")
        self.assertEqual(doc.form_version, "2018-01")
        needs = json.loads(doc.needs)
        self.assertTrue(any(n["key"] == "engine" for n in needs))
        self.assertEqual(doc.status, "Draft")
        with self.assertRaises(frappe.ValidationError):
            doc.submit()
        doc.reload()
        self.assertEqual(doc.docstatus, 0)

    def test_preview_slots_are_limited(self):
        from ph_cas.ph_cas.doctype.ph_tax_return.ph_tax_return import PREVIEWS_PER_MINUTE, take_preview_slot

        frappe.cache().delete_value("ph_preview:limit.test")
        for _ in range(PREVIEWS_PER_MINUTE):
            self.assertTrue(take_preview_slot("limit.test", now=1000.0))
        self.assertFalse(take_preview_slot("limit.test", now=1000.0))
        self.assertTrue(take_preview_slot("limit.test", now=1100.0))
