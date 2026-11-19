"""B78 (LDG-52): the print pack for the paper check: a cover with the 100 mm bar and the checklist,
the latest invoice, credit note, collection receipt and 2307 stamped SPECIMEN with a 100 mm bar,
no print counted, Accounting Managers only; and the PDF engine draws at true size (the image
installs wkhtmltopdf with patched Qt; a bench with the Debian package skips that one check)."""

import subprocess

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.qa import fullpass


def _patched() -> bool:
    try:
        return "patched qt" in subprocess.run(["wkhtmltopdf", "--version"], capture_output=True, text=True).stdout
    except OSError:
        return False


def _assets_built() -> bool:
    """Frappe's print page needs the compiled assets (assets.json); the CI bench does not build them."""
    from frappe.utils import get_assets_json

    try:
        return bool(get_assets_json())
    except Exception:
        return False


class TestB78PaperCheck(IntegrationTestCase):
    def test_paper_check_section(self):
        if not _assets_built():
            self.skipTest("no compiled assets on this bench: the print page cannot render (the full pass runs it on staging)")
        frappe.set_user("Administrator")
        for section in ("companies", "purchasing", "sales", "paper_check"):
            res = fullpass.run(section)
            failed = [f"{s['step']}: {s['detail']}" for s in res["steps"] if not s["ok"]
                      and not (s["step"].startswith("the PDF is at true size") and not _patched())]
            self.assertFalse(failed, f"{section}: {failed}")
