"""B31: backups, verification and monitoring."""

import json
import os

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.ops.backup import decrypt_file, run_backup, verify_backup
from ph_cas.ops.monitor import status


class TestB31Ops(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_backup_with_files_manifest_and_encryption_round_trip(self):
        frappe.conf.ph_backup_key = "test-key-123"
        try:
            out = run_backup(encrypt=True, upload=False)
        finally:
            frappe.conf.pop("ph_backup_key", None)
        self.assertTrue(os.path.exists(out["manifest"]))
        manifest = json.load(open(out["manifest"]))
        names = list(manifest["files"])
        self.assertTrue(any(n.endswith("-database.sql.gz") for n in names))
        self.assertTrue(any("files" in n for n in names), names)
        enc = [p for p in out["files"] if p.endswith(".enc")]
        self.assertTrue(enc)
        v = verify_backup(out["manifest"], key="test-key-123")
        self.assertTrue(v["ok"], v)
        db_enc = [p for p in enc if "database" in p][0]
        plain = decrypt_file(db_enc, "test-key-123", db_enc + ".check")
        import gzip

        found = False
        with gzip.open(plain, "rb") as f:
            for line in f:
                if b"CREATE TABLE `tabPH Event Log`" in line:
                    found = True
                    break
        self.assertTrue(found)
        os.remove(plain)
        self.assertTrue(frappe.db.get_single_value("PH CAS Settings", "last_backup_on"))

    def test_wrong_key_fails_verification(self):
        frappe.conf.ph_backup_key = "right-key"
        try:
            out = run_backup(encrypt=True, upload=False)
        finally:
            frappe.conf.pop("ph_backup_key", None)
        with self.assertRaises(Exception):
            verify_backup(out["manifest"], key="wrong-key")

    def test_status_reports_every_check(self):
        st = status()
        for k in ("backup_ok", "chain_ok", "disk_ok", "draft_rules_ok", "ok", "disk_free_gb", "draft_rules"):
            self.assertIn(k, st)
        self.assertTrue(st["draft_rules_ok"])  # not a production site
        from ph_cas.tax.rules import apply_acceptance

        apply_acceptance()
        frappe.conf.ph_cas_production = 1
        try:
            self.assertTrue(status()["draft_rules_ok"])  # every seeded rule is accepted (LDG-47)
            frappe.get_doc({"doctype": "PH Tax Rule", "rule_id": "QA-DRAFT-OPS", "kind": "percentage", "title": "x", "atc": "PTQAO", "base": "gross", "rate": 1, "effective_from": "2026-01-01", "legal_basis": "test", "status": "draft"}).insert()
            self.assertFalse(status()["draft_rules_ok"])  # a draft exists; production refuses it
        finally:
            frappe.conf.pop("ph_cas_production", None)
