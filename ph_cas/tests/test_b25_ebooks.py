"""B25: year-end e-books pack (CSV until the RR 16-2006 format arrives)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, today

from ph_cas.books.yearend import BOOKS, build_pack, verify_pack
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import make_journal_entry
from ph_cas.tests.setup import TEST_COMPANY


class TestB25Ebooks(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        make_journal_entry()

    def test_pack_has_every_book_manifest_and_transmittal(self):
        out = build_pack(TEST_COMPANY, getdate(today()).year)
        names = set(out["files"])
        self.assertIn("MANIFEST.json", names)
        self.assertIn("TRANSMITTAL.txt", names)
        self.assertEqual(len(names), len(BOOKS) + 3)  # manifest, transmittal, file layout
        gj = [n for n in names if n.endswith("_GJ.csv")][0]
        text = out["files"][gj].decode("utf-8-sig")
        self.assertIn("Software: PH CAS", text)
        self.assertIn("TIES TO THE LEDGER", text)
        self.assertTrue(verify_pack(out["files"])["ok"])
        t = out["files"]["TRANSMITTAL.txt"].decode("utf-8")
        self.assertIn("RMO 9-2021", t)
        self.assertIn("ORUS QR stamp", t)
        self.assertIn("SHA-256", t)

    def test_tampered_file_fails_verification(self):
        out = build_pack(TEST_COMPANY, getdate(today()).year)
        gj = [n for n in out["files"] if n.endswith("_GJ.csv")][0]
        out["files"][gj] = out["files"][gj] + b"x"
        v = verify_pack(out["files"])
        self.assertFalse(v["ok"])
        self.assertEqual(v["bad"], [gj])
