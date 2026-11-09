"""B36: enterprise pair scripts and runbook are present, valid shell, and consistent with the backup scheme."""

import os
import subprocess

import frappe
from frappe.tests import IntegrationTestCase

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestB36Enterprise(IntegrationTestCase):
    def test_scripts_exist_and_parse(self):
        for rel in ("scripts/enterprise/provision-pair.sh", "scripts/enterprise/standby-restore-test.sh", "deploy/ledger-site.sh", "deploy/entrypoint.sh"):
            p = os.path.join(ROOT, rel)
            self.assertTrue(os.path.exists(p), rel)
            subprocess.run(["bash", "-n", p], check=True)

    def test_restore_test_uses_the_same_cipher_as_the_backup_module(self):
        src = open(os.path.join(ROOT, "scripts/enterprise/standby-restore-test.sh"), encoding="utf-8").read()
        self.assertIn("-aes-256-cbc", src)
        self.assertIn("-pbkdf2", src)
        from ph_cas.ops import backup

        self.assertIn("-pbkdf2", open(backup.__file__, encoding="utf-8").read())

    def test_runbook_and_image_workflow(self):
        rb = open(os.path.join(ROOT, "docs/runbooks/enterprise-pair.md"), encoding="utf-8").read()
        for s in ("## Provisioning", "## Nightly restore test", "## Failover", "## SLA", "ghcr.io/markchrc2025/ph-cas"):
            self.assertIn(s, rb)
        wf = open(os.path.join(ROOT, ".github/workflows/image.yml"), encoding="utf-8").read()
        self.assertIn("ghcr.io/${{ github.repository }}:latest", wf)
        self.assertIn("packages: write", wf)
