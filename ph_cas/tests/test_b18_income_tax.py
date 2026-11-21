"""B18: income tax figures."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, getdate, today

from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.income_tax import graduated_tax
from ph_cas.tax.returns import get_or_create, quarter_bounds
from ph_cas.tests.fixtures import acc, make_journal_entry
from ph_cas.tests.setup import TEST_COMPANY


def _company(**fields):
    for k, v in fields.items():
        frappe.db.set_value("Company", TEST_COMPANY, k, v, update_modified=False)
    frappe.clear_document_cache("Company", TEST_COMPANY)


def _je(debit_acc, credit_acc, amount):
    je = frappe.get_doc({"doctype": "Journal Entry", "company": TEST_COMPANY, "voucher_type": "Journal Entry", "posting_date": today(), "accounts": [
        {"account": debit_acc, "debit_in_account_currency": amount, "cost_center": acc("Main")},
        {"account": credit_acc, "credit_in_account_currency": amount, "cost_center": acc("Main")}]}).insert()
    je.submit()
    return je


class TestB18IncomeTax(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _company(ph_income_tax_option="Corporate", ph_deduction_method="Itemized", ph_corp_small=0, ph_operations_start_year=0, ph_primary_business="Services", ph_mixed_income=0)
        self.year = getdate(today()).year
        self.qs, self.qe = quarter_bounds(today())

    def tearDown(self):
        _company(ph_income_tax_option="Corporate", ph_deduction_method="Itemized", ph_corp_small=0, ph_operations_start_year=0)

    def fig(self, form, start=None, end=None):
        start = start or f"{self.year}-01-01"
        end = end or f"{self.year}-12-31"
        doc = get_or_create(TEST_COMPANY, form, start, end)
        return doc, {r.item: flt(r.amount) for r in doc.lines}

    def test_graduated_table(self):
        self.assertEqual(graduated_tax(250000), 0)
        self.assertEqual(graduated_tax(400000), 22500)
        self.assertEqual(graduated_tax(800000), 102500)
        self.assertEqual(graduated_tax(2000000), 402500)
        self.assertEqual(graduated_tax(8000000), 2202500)
        self.assertEqual(graduated_tax(1000000), 102500 + 50000)

    def test_corporate_rcit_and_credits(self):
        d0, f0 = self.fig("1702-RT")
        _je(acc("Cash"), acc("Sales"), 100000)
        _je(acc("Administrative Expenses"), acc("Cash"), 40000)
        d, f = self.fig("1702-RT")
        self.assertEqual(f["Sales"] - f0["Sales"], 100000)
        self.assertEqual(f["Ordinary deductions"] - f0["Ordinary deductions"], 40000)
        self.assertEqual(f["Taxable income"] - f0["Taxable income"], 60000)
        self.assertEqual(f["RCIT"], flt(max(f["Taxable income"], 0) * 0.25, 2))
        self.assertEqual(f["Tax due"], max(f["RCIT"], f["MCIT"]))
        self.assertEqual(f["Payable"], flt(f["Tax due"] - f["Credits 2307"] - f["Prior quarters"], 2))

    def test_small_corporation_rate(self):
        _company(ph_corp_small=1)
        d, f = self.fig("1702-RT")
        self.assertEqual(f["RCIT"], flt(max(f["Taxable income"], 0) * 0.20, 2))

    def test_mcit_applies_from_the_fourth_year(self):
        _company(ph_operations_start_year=self.year - 1)
        d, f = self.fig("1702-RT")
        self.assertEqual(f["MCIT"], 0)
        _company(ph_operations_start_year=self.year - 4)
        d, f = self.fig("1702-RT")
        self.assertEqual(f["MCIT"], flt(max(f["Gross income"], 0) * 0.02, 2))
        self.assertEqual(f["Tax due"], max(f["RCIT"], f["MCIT"]))
        self.assertEqual(f["Excess MCIT"], flt(max(f["MCIT"] - f["RCIT"], 0), 2))

    def test_ear_cap_and_non_deductible_add_back(self):
        ear = frappe.get_doc("Account", acc("Entertainment Expenses"))
        ear.ph_tax_class = "Entertainment, amusement and recreation"
        ear.save()
        nd = frappe.get_doc("Account", acc("Legal Expenses"))
        nd.ph_tax_class = "Non-deductible"
        nd.save()
        d0, f0 = self.fig("1702-RT")
        _je(acc("Cash"), acc("Sales"), 100000)
        # cap is 1% of the year's sales: post enough entertainment to pass it, whatever the
        # test site already holds for the year
        spend = max(5000, flt((f0["Sales"] + 100000) * 0.01 - f0["EAR"] + 5000, 2))
        _je(acc("Entertainment Expenses"), acc("Cash"), spend)
        _je(acc("Legal Expenses"), acc("Cash"), 700)
        d, f = self.fig("1702-RT")
        self.assertEqual(f["EAR"], min(f0["EAR"] + spend, flt(f["Sales"] * 0.01, 2)))
        self.assertGreater(f["EAR excess"], 0)
        self.assertEqual(f["Non-deductible"] - f0["Non-deductible"], 700)
        from ph_cas.ph_cas.report.ph_book_to_tax_reconciliation.ph_book_to_tax_reconciliation import execute

        cols, rows = execute({"company": TEST_COMPANY, "from_date": f"{self.year}-01-01", "to_date": f"{self.year}-12-31"})
        self.assertEqual(next(r for r in rows if r["line"].startswith("Unexplained difference"))["amount"], 0)

    def test_osd(self):
        _company(ph_deduction_method="OSD (40%)")
        d, f = self.fig("1702-RT")
        self.assertEqual(f["Deductions"], flt(f["Gross income"] * 0.40, 2))
        self.assertEqual(f["NOLCO"], 0)

    def test_individual_graduated_and_8_percent(self):
        _company(ph_income_tax_option="Graduated (individual)", ph_deduction_method="OSD (40%)")
        d, f = self.fig("1701")
        self.assertEqual(f["Deductions"], flt(f["Sales"] * 0.40, 2))
        self.assertEqual(f["Tax due"], graduated_tax(f["Taxable income"]))
        _company(ph_income_tax_option="8% option (individual)", ph_mixed_income=0)
        d, f = self.fig("1701A")
        self.assertEqual(f["Base"], max(flt(f["Sales"] - 250000, 2), 0))
        self.assertEqual(f["Tax due"], flt(f["Base"] * 0.08, 2))
        _company(ph_mixed_income=1)
        d, f = self.fig("1701")
        self.assertEqual(f["Base"], f["Sales"])

    def test_nolco_record_and_application(self):
        n = frappe.get_doc({"doctype": "PH NOLCO", "company": TEST_COMPANY, "loss_year": self.year - 1, "amount": 1000}).insert()
        self.assertEqual(n.carry_years, 3)
        self.assertEqual(n.expiry_year, self.year + 2)
        n2 = frappe.get_doc({"doctype": "PH NOLCO", "company": TEST_COMPANY, "loss_year": 2021, "amount": 500}).insert()
        self.assertEqual(n2.carry_years, 5)
        d, f = self.fig("1702-RT")
        if f["Taxable income"] + f["NOLCO"] > 0:
            self.assertGreater(f["NOLCO"], 0)
        q, fq = self.fig("1702Q", self.qs, self.qe)
        self.assertEqual(fq["NOLCO"], 0)  # quarterly returns leave NOLCO to the annual return

    def test_quarterly_is_cumulative_and_nets_prior_quarters(self):
        q, fq = self.fig("1702Q", self.qs, self.qe)
        self.assertEqual(fq["Payable"], flt(fq["Tax due"] - fq["Credits 2307"] - fq["Prior quarters"], 2))
