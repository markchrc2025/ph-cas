"""B64 (QA pass 3): income tax returns built through PH Tax Return, the way the app builds
them, take the Company's income tax options (MCIT, rate, OSD, 8%) and the payments of the
filed quarterly returns of the year."""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, today

from ph_cas.ph_cas.doctype.ph_tax_return.ph_tax_return import new_return
from ph_cas.qa import api
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.setup import TEST_COMPANY


def lines(name):
    return {r.item: r.amount for r in frappe.get_all("PH Tax Return Line", filters={"parent": name}, fields=["item", "amount"])}


def built(form, key, company=TEST_COMPANY):
    name = new_return(company, form, key)
    doc = frappe.get_doc("PH Tax Return", name)
    doc.refresh_from_books()
    doc.reload()
    return doc


def as_filed(doc):
    """Stand-in for filing (which needs the BIR's confirmation): seal the return as filed."""
    frappe.db.set_value("PH Tax Return", doc.name, "docstatus", 1, update_modified=False)
    frappe.db.sql("update `tabPH Tax Return Line` set docstatus = 1 where parent = %s", doc.name)


class TestB64IncomeFeeds(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        qs, _ = quarter_bounds(today())
        if getdate(qs).month < 10:
            self.skipTest("needs the fourth quarter, with three earlier quarters in the year")
        self.year = getdate(today()).year
        for n in frappe.get_all("PH Tax Return", filters={"form": ("in", ["1702Q", "1702-RT", "1701Q"]), "period_start": (">=", f"{self.year}-01-01")}, pluck="name"):
            frappe.db.delete("PH Tax Return Line", {"parent": n})
            frappe.db.delete("PH Tax Return", n)

    def test_corporation_mcit_and_quarter_payments(self):
        y = self.year
        with patch.dict(frappe.conf, {"ph_staging_site": 1, "ph_cas_production": 0}), patch.object(frappe.db, "commit"):
            api.seed_scenario("income_year", TEST_COMPANY)
        q1 = built("1702Q", f"{y}-Q1")
        by = lines(q1.name)
        # MCIT applies (operations from 2020): both computations show; the regular tax is higher
        self.assertEqual(by["Sch 2.11"], 35625)
        self.assertEqual(by["Sch 2.12"], 6000)
        self.assertEqual(by["Sch 2.13"], 35625)
        self.assertEqual(by["20"], 32625)
        as_filed(q1)

        q3 = built("1702Q", f"{y}-Q3")
        by = lines(q3.name)
        self.assertEqual(by["Sch 2.12"], 18000)
        self.assertEqual(by["Sch 4.2"], 32625)  # Q1's payment; Q2 was not filed
        self.assertIn(f"No filed 1702Q in Ledger for Q2 {y}", q3.warnings or "")
        self.assertEqual(by["20"], 106875 - 32625 - 9000)

        rt = built("1702-RT", f"{y}")
        data = json.loads(rt.data)
        self.assertEqual(data["mcit"], "yes")
        self.assertEqual(data["i46"], "32625")
        self.assertEqual(data["i45"], "0")
        self.assertIn(f"No filed 1702Q in Ledger for Q2, Q3 {y}", rt.warnings or "")

    def test_individual_osd_and_atc_from_the_company(self):
        y = self.year
        with patch.dict(frappe.conf, {"ph_staging_site": 1, "ph_cas_production": 0}), patch.object(frappe.db, "commit"):
            out = api.seed_scenario("individual_year")
        name = out["company_created"]
        q3 = built("1701Q", f"{y}-Q3", name)
        data = json.loads(q3.data)
        self.assertEqual(data["methodA"], "osd")
        self.assertEqual(data["rateA"], "graduated")
        self.assertEqual(data["atc"], "II012")
        self.assertNotIn("data.atc", q3.needs or "")
        by = lines(q3.name)
        # sales 900,000 to date, OSD 40%: taxable 540,000; 22,500 + 20% over 400,000
        self.assertEqual(by["28/63A"], 50500)
