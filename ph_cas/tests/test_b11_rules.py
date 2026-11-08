"""B11: tax rules table, resolver, sign-off."""

import os
import tempfile

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.tax.rules import PHDraftRuleError, PHNoRuleError, apply_signoff, rate, resolve, seed, seed_count


class TestB11Rules(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        seed()

    def test_seed_covers_every_row_and_all_are_draft(self):
        self.assertEqual(frappe.db.count("PH Tax Rule"), seed_count())
        self.assertGreaterEqual(seed_count(), 60)
        self.assertEqual(frappe.db.count("PH Tax Rule", {"status": "draft"}), seed_count())

    def test_resolution_by_date_picks_the_right_version(self):
        self.assertEqual(rate("percentage", "2019-06-30", "PT010"), 3)
        self.assertEqual(rate("percentage", "2021-06-30", "PT010"), 1)
        self.assertEqual(rate("percentage", "2026-11-09", "PT010"), 3)
        self.assertEqual(rate("income", "2022-01-01", taxpayer="corporation", mcit="1"), 1)
        self.assertEqual(rate("income", "2026-01-01", taxpayer="corporation", mcit="1"), 2)

    def test_selectors_pick_the_most_specific_rule(self):
        r = resolve("ewt", "2026-01-01", category="professional", payee_type="Individual", over_threshold="0")
        self.assertEqual(r.atc, "WI010")
        self.assertEqual(float(r.rate), 5)
        r = resolve("ewt", "2026-01-01", category="professional", payee_type="Non-individual", over_threshold="1")
        self.assertEqual(r.atc, "WC011")
        self.assertEqual(float(r.rate), 15)
        self.assertEqual(rate("vat", "2026-01-01", **{"class": "VATable"}), 12)
        self.assertEqual(rate("vat", "2026-01-01", **{"class": "Zero-rated"}), 0)

    def test_no_rule_before_effectivity(self):
        with self.assertRaises(PHNoRuleError):
            resolve("vat_withholding", "2025-01-01", "WV080", supplier="nonresident_dsp", payor="private")
        self.assertEqual(rate("vat_withholding", "2025-07-01", "WV080", supplier="nonresident_dsp", payor="private"), 12)

    def test_overlapping_rules_are_refused(self):
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({"doctype": "PH Tax Rule", "rule_id": "PT-DUP", "kind": "percentage", "title": "dup", "atc": "PT010", "base": "gross", "rate": 3, "effective_from": "2024-01-01", "legal_basis": "test"}).insert()

    def test_production_refuses_draft_rules(self):
        frappe.conf.ph_cas_production = 1
        try:
            with self.assertRaises(PHDraftRuleError):
                resolve("percentage", "2026-01-01", "PT010")
            self.assertEqual(rate("percentage", "2026-01-01", "PT010", allow_draft=True), 3)
        finally:
            frappe.conf.pop("ph_cas_production", None)

    def test_signoff_flips_only_listed_rules_and_locks_them(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("# Sign-off\nConfirmed by Juan Dela Cruz, CPA, 9 Nov 2026 (signed)\n\n- PT-3-RESTORED\n- [x] VAT-OUT-12\n- NOT-A-RULE\n")
            path = f.name
        try:
            out = apply_signoff(path)
        finally:
            os.unlink(path)
        self.assertEqual(sorted(out["confirmed"]), ["PT-3-RESTORED", "VAT-OUT-12"])
        self.assertEqual(out["missing"], ["NOT-A-RULE"])
        self.assertEqual(frappe.db.get_value("PH Tax Rule", "PT-3-RESTORED", "status"), "confirmed")
        self.assertEqual(frappe.db.get_value("PH Tax Rule", "PT-1-CREATE", "status"), "draft")
        frappe.conf.ph_cas_production = 1
        try:
            self.assertEqual(rate("percentage", "2026-01-01", "PT010"), 3)
        finally:
            frappe.conf.pop("ph_cas_production", None)
        doc = frappe.get_doc("PH Tax Rule", "PT-3-RESTORED")
        doc.rate = 4
        with self.assertRaises(frappe.ValidationError):
            doc.save()
        doc.reload()
        doc.status = "draft"
        with self.assertRaises(frappe.ValidationError):
            doc.save()
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("PH Tax Rule", "PT-3-RESTORED")

    def test_signoff_file_must_be_signed(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("- PT-3-RESTORED\n")
            path = f.name
        try:
            with self.assertRaises(frappe.ValidationError):
                apply_signoff(path)
        finally:
            os.unlink(path)

    def test_draft_report_lists_drafts(self):
        from ph_cas.ph_cas.report.ph_draft_tax_rules.ph_draft_tax_rules import execute

        cols, rows = execute({})
        self.assertTrue(rows)
