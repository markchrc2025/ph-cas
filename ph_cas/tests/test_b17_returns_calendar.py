"""B17: 2551Q, 0619-E, 1601-EQ, 1600-VT figures and the compliance calendar."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, get_first_day, get_last_day, getdate, today

from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tax.calendar import applicable_forms, calendar, due_dates, next_working_day
from ph_cas.tax.returns import get_or_create, quarter_bounds
from ph_cas.tests.fixtures import ensure_service_item, ensure_supplier_profile, make_purchase_invoice
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_b12_sales_vat import _invoice, _item, _set_regime


class TestB17ReturnsCalendar(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        _set_regime("Non-VAT")
        self.qs, self.qe = quarter_bounds(today())
        self.ms, self.me = get_first_day(today()), get_last_day(today())

    def fig(self, form, start, end):
        doc = get_or_create(TEST_COMPANY, form, start, end)
        return doc, {r.item: flt(r.amount) for r in doc.lines}

    def test_2551q_from_percentage_tax_base(self):
        d0, f0 = self.fig("2551Q", self.qs, self.qe)
        _invoice([(_item("_PH VATable", "VATable"), 1, 10000, {})], submit=True)
        d, f = self.fig("2551Q", self.qs, self.qe)
        self.assertEqual(f["S1.1 base"] - f0["S1.1 base"], 10000)
        self.assertEqual(f["S1.1 rate"], 3)
        self.assertEqual(f["14"] - f0["14"], 300)
        self.assertEqual(f["24"], flt(f["14"] - f["18"], 2))
        self.assertEqual(d.period_label, f"{self.qs.year}-Q{(self.qs.month - 1) // 3 + 1}")

    def test_0619e_and_1601eq_tie(self):
        sup = ensure_supplier_profile("_Test PH Contractor", ph_vat_status="Non-VAT", ph_payee_type="Non-individual", ph_ewt_category="contractor")
        d0, m0 = self.fig("0619-E", self.ms, self.me)
        q0, f0 = self.fig("1601-EQ", self.qs, self.qe)
        make_purchase_invoice(sup, [(ensure_service_item(), 1, 5000, {})], submit=True)
        d, m = self.fig("0619-E", self.ms, self.me)
        q, f = self.fig("1601-EQ", self.qs, self.qe)
        self.assertEqual(m["14"] - m0["14"], 100)
        self.assertEqual(f["19"] - f0["19"], 100)
        self.assertEqual(d.period_label, today()[:7])
        # the quarter's total equals the sum of the three months
        months = []
        from frappe.utils import add_months

        for i in range(3):
            s = add_months(self.qs, i)
            months.append(self.fig("0619-E", get_first_day(s), get_last_day(s))[1]["14"])
        self.assertEqual(flt(sum(months), 2), f["19"])
        self.assertEqual(f["26"], flt(f["19"] - f["25"], 2))
        atc_rows = [r for r in q.lines if r.item.endswith(" tax")]
        self.assertTrue(any("WC120" in r.label for r in atc_rows))

    def test_1600vt_from_reverse_charge(self):
        _set_regime("VAT")
        try:
            dsp = ensure_supplier_profile("_Test PH Cloud Provider", ph_is_nonresident_dsp=1, ph_vat_status="Non-VAT")
            d0, f0 = self.fig("1600-VT", self.ms, self.me)
            make_purchase_invoice(dsp, [(ensure_service_item(), 1, 1000, {})], submit=True)
            d, f = self.fig("1600-VT", self.ms, self.me)
            self.assertEqual(f["WV080 tax"] - f0.get("WV080 tax", 0), 120)
            self.assertEqual(f["Total"] - f0["Total"], 120)
        finally:
            _set_regime("Non-VAT")

    def test_due_dates_and_weekend_rule(self):
        hol = getdate("2026-12-25")  # Friday, Christmas
        self.assertEqual(next_working_day(hol, {hol}), getdate("2026-12-28"))
        self.assertEqual(next_working_day(getdate("2026-11-14")), getdate("2026-11-16"))  # Saturday
        q = due_dates("2550Q", 2026)
        self.assertEqual([d["period_label"] for d in q], ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"])
        self.assertEqual(q[0]["due"], next_working_day(getdate("2026-04-25")))
        self.assertEqual(q[3]["due"], next_working_day(getdate("2027-01-25")))
        e = due_dates("0619-E", 2026)
        self.assertEqual(len(e), 8)  # months 1 and 2 of each quarter
        self.assertEqual(e[0]["due"], next_working_day(getdate("2026-02-10")))
        eq = due_dates("1601-EQ", 2026)
        self.assertEqual(eq[0]["due"], next_working_day(getdate("2026-04-30")))
        self.assertEqual(due_dates("1604-E", 2026)[0]["due"], next_working_day(getdate("2027-03-01")))
        self.assertEqual(due_dates("1702Q", 2026)[0]["due"], next_working_day(getdate("2026-05-30")))
        self.assertEqual(due_dates("1701Q", 2026)[1]["due"], next_working_day(getdate("2026-08-15")))
        self.assertEqual(due_dates("1702-RT", 2026)[0]["due"], next_working_day(getdate("2027-04-15")))

    def test_calendar_lists_applicable_forms_with_status(self):
        forms = applicable_forms(TEST_COMPANY)
        self.assertIn("2551Q", forms)
        self.assertNotIn("2550Q", forms)
        self.assertIn("1702Q", forms)
        rows = calendar(TEST_COMPANY, getdate(today()).year)
        self.assertTrue(rows)
        statuses = {r["status"] for r in rows}
        self.assertTrue(statuses & {"Period open", "Due, not computed", "Computed, not filed", "OVERDUE, nothing computed", "Filed"})
        self.assertEqual(rows, sorted(rows, key=lambda r: (r["due"], r["form"])))

    def test_holidays_seeded(self):
        self.assertTrue(frappe.db.exists("PH Holiday", {"holiday_date": f"{getdate(today()).year}-12-25"}))
