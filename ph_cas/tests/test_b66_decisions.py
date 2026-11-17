"""B66 (LDG-46): the owner's decisions of 17 Nov 2026. D10: Christian R. Canlubo signs every
client's joint sworn statement; the branding pass fills him in where the setting is blank and
leaves an edited value alone. DECISIONS.md carries no unconfirmed decision except D3 (waits on LDG-54)."""

import os

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas import branding

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestB66Decisions(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.flags.mute_emails = True

    def tearDown(self):
        frappe.flags.mute_emails = False

    def _settings(self, **values):
        frappe.db.set_single_value("PH CAS Settings", values)
        frappe.clear_document_cache("PH CAS Settings", "PH CAS Settings")

    def test_signatory_filled_in_when_blank(self):
        self._settings(provider_signatory="", provider_signatory_position="")
        branding.apply("Sentire Ledger", "MCRC Tax and Accounting Services")
        s = frappe.get_single("PH CAS Settings")
        self.assertEqual(s.provider_signatory, "Christian R. Canlubo")
        self.assertEqual(s.provider_signatory_position, "Owner")

        from ph_cas.registration.pack import joint_sworn_statement

        company = frappe.get_all("Company", limit=1, pluck="name")[0]
        text = joint_sworn_statement(company)
        self.assertIn("We, Christian R. Canlubo, Owner of MCRC Tax and Accounting Services", text)
        self.assertNotIn("[PROVIDER SIGNATORY", text)

    def test_an_edited_signatory_stays(self):
        self._settings(provider_signatory="Someone Else", provider_signatory_position="Proprietor")
        branding.apply("Sentire Ledger", "MCRC Tax and Accounting Services")
        s = frappe.get_single("PH CAS Settings")
        self.assertEqual((s.provider_signatory, s.provider_signatory_position), ("Someone Else", "Proprietor"))

    def test_decisions_file(self):
        with open(os.path.join(ROOT, "docs", "DECISIONS.md")) as f:
            rows = [l for l in f.read().split("## Loose-leaf")[0].splitlines() if l.startswith("| ") and not l.startswith("| #")]
        status = {r.split("|")[1].strip(): r.split("|")[4].strip() for r in rows}
        self.assertEqual({k for k, v in status.items() if not v.startswith("confirmed")}, {"D3"})
        self.assertNotIn("open", status.values())
