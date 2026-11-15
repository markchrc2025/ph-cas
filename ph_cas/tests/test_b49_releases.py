"""B49: the release log and the quarterly notice of minor enhancements (LDG-99)."""

import frappe
from frappe.tests import IntegrationTestCase

import ph_cas
from ph_cas.ops.releases import check_log, minor_releases_in, quarter_bounds, quarterly_notice, releases
from ph_cas.tests.setup import TEST_COMPANY

LOG = [
    {"version": "1.0.0", "date": "2026-11-15", "class": "major", "summary": "First release for registration.", "items": []},
    {"version": "1.0.1", "date": "2027-01-20", "class": "minor", "summary": "Fixes", "items": ["The customer field is a searchable dropdown.", "A rounding fix on the VAT line."]},
    {"version": "1.1.0", "date": "2027-03-02", "class": "minor", "summary": "Faster books", "items": ["The General Ledger opens faster."]},
    {"version": "1.1.1", "date": "2027-04-05", "class": "minor", "summary": "Fix", "items": ["A label."]},
]


class TestB49Releases(IntegrationTestCase):
    def test_the_shipped_log_is_valid_and_names_the_running_version(self):
        self.assertEqual(check_log(), [])
        shipped = releases()
        if shipped:  # empty until the owner declares the product done (then 1.0.0, major)
            self.assertEqual(shipped[-1]["version"], ph_cas.__version__)
            self.assertEqual(shipped[0]["class"], "major")

    def test_the_log_check_enforces_the_major_version_rule(self):
        self.assertEqual(check_log(LOG), [])
        bad = LOG + [{"version": "2.0.1", "date": "2027-05-01", "class": "minor", "items": []}]
        self.assertTrue(any("stays within major version 1" in p for p in check_log(bad)))
        bad = LOG + [{"version": "1.2.0", "date": "2027-05-01", "class": "major", "items": []}]
        self.assertTrue(any("starts the next major version" in p for p in check_log(bad)))
        bad = LOG + [{"version": "1.1.2", "date": "2027-05-01", "class": "patch", "items": []}]
        self.assertTrue(any("major or minor" in p for p in check_log(bad)))

    def test_quarters(self):
        self.assertEqual([str(d) for d in quarter_bounds(2027, 1)], ["2027-01-01", "2027-03-31"])
        self.assertEqual([str(d) for d in quarter_bounds(2026, 4)], ["2026-10-01", "2026-12-31"])
        self.assertEqual([r["version"] for r in minor_releases_in(2027, 1, LOG, "1.1.1")], ["1.0.1", "1.1.0"])

    def test_quarterly_notice_lists_the_quarter_minor_releases(self):
        text = quarterly_notice(TEST_COMPANY, 2027, 1, LOG, "1.1.1")
        self.assertIn("Section V.9 of RMO No. 9-2021", text)
        self.assertIn("from version 1.0.0 to version 1.1.0", text)
        self.assertIn("  - The customer field is a searchable dropdown.", text)
        self.assertIn("  - The General Ledger opens faster.", text)
        self.assertNotIn("A label.", text)
        self.assertTrue(text.endswith("\r\n"))

    def test_a_quarter_without_minor_releases_needs_no_notice(self):
        self.assertIsNone(quarterly_notice(TEST_COMPANY, 2026, 4, LOG, "1.1.1"))
        with self.assertRaises(frappe.ValidationError):
            from ph_cas.ops.releases import download_quarterly_notice

            download_quarterly_notice(TEST_COMPANY, 2026, 4)
