"""B63: the staging scenarios for QA pass 3 (income tax from the books) give the figures worked
out by hand below."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, today

from ph_cas.qa import api
from ph_cas.tax.income_tax import compute_1701q, compute_1702q
from ph_cas.tax.returns import quarter_bounds
from ph_cas.tests.setup import TEST_COMPANY


def figures(lines):
    return {k: v for k, _label, v, _src in lines}


class TestB63QAIncome(IntegrationTestCase):
    def test_income_year_and_individual_year(self):
        qs, _qe = quarter_bounds(today())
        last_q_end = frappe.utils.add_days(qs, -1)
        months = getdate(last_q_end).month
        if months == 12 or months < 3:
            self.skipTest("needs a quarter before the current one in the same year")
        year = getdate(today()).year
        with patch.dict(frappe.conf, {"ph_staging_site": 1, "ph_cas_production": 0}), patch.object(frappe.db, "commit"):
            made = api.seed_scenario("income_year", TEST_COMPANY)
            self.assertEqual(made["months"], months)
            again = api.seed_scenario("income_year", TEST_COMPANY)
            self.assertEqual(again["sales_invoices"], made["sales_invoices"])  # nothing twice
            f = figures(compute_1702q(TEST_COMPANY, f"{year}-01-01", str(last_q_end)))
            self.assertEqual(f["Sales"], 250000 * months)
            self.assertEqual(f["COGS"], 150000 * months)
            self.assertEqual(f["Gross income"], 100000 * months)
            self.assertEqual(f["EAR"], 2500 * months)  # 1% of sales (services), the rest added back
            self.assertEqual(f["EAR excess"], 2500 * months)
            self.assertEqual(f["Taxable income"], 100000 * months - 50000 * months - 2500 * months)
            self.assertEqual(f["RCIT"], round((47500 * months) * 0.25, 2))
            self.assertEqual(f["MCIT"], 2000 * months)  # 2% of gross income, operations began 2020
            self.assertEqual(f["Credits 2307"], 3000 * (months // 3))

            out = api.seed_scenario("individual_year")
            name = out["company_created"]
            self.assertEqual(frappe.db.get_value("Company", name, "ph_taxpayer_type"), "Individual")
            g = figures(compute_1701q(name, f"{year}-01-01", str(last_q_end)))
            sales = 100000 * months
            self.assertEqual(g["Sales"], sales)
            self.assertEqual(g["Deductions"], sales * 0.4)
            self.assertEqual(g["Taxable income"], sales * 0.6)
