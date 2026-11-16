"""B59 (LDG-49): Ledger computes every return the way eBIRForms v7.9.6.2 does.

Each file in tests/data/ebirforms_parity holds a scenario (the inputs) and the figures
eBIRForms itself computed for it: the form unpacked by BIRForms.exe, the inputs typed in,
and every computed field read back. The Ledger engine must give the same figures, field
by field: the export for forms with an eBIRForms file, the computed items for the rest.
"""

import glob
import importlib
import json
import os
from decimal import Decimal

from frappe.tests import IntegrationTestCase

from ph_cas.forms.engine import Context
from ph_cas.forms.money import amt
from ph_cas.forms.period import parse as parse_period
from ph_cas.forms.registry import spec
from ph_cas.tests.setup import TEST_COMPANY
from ph_cas.tests.test_f1_2551q import TAXPAYER
from ph_cas.tests.test_g3_income_tax import INDIVIDUAL

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ebirforms_parity")


def ledger_figures(sc: dict) -> dict[str, str]:
    s = spec(sc["form"])
    base = INDIVIDUAL if sc.get("taxpayer") == "individual" else TAXPAYER
    c = dict(base, name=TEST_COMPANY, company_name=TEST_COMPANY, **sc.get("company", {}))
    ctx = Context(s, parse_period(sc["period"], s.period), c, contact_number="09170000000", return_name="T", is_amended=bool(sc.get("amended")))
    mod = importlib.import_module("ph_cas.forms.f" + s.key.lower())
    comp = mod.compute(sc["data"], ctx)
    if sc.get("map"):
        by = {str(ln["item"]): ln["amount"] for ln in comp}
        return {eid: amt(by[item]) for eid, item in sc["map"].items()}
    rows, _name = mod.export_rows(sc["data"], comp, ctx)
    return {k.split(":", 1)[-1] if k.startswith(s.namespace + ":") else k: v for k, v in rows}


def number(v) -> Decimal:
    """An eBIRForms figure: "1,234.50", "1,234" or "(1,234)" (a negative in parentheses)."""
    t = str(v).replace(",", "").strip()
    neg = t.startswith("(") and t.endswith(")")
    d = Decimal(t.strip("()") or "0").quantize(Decimal("0.01"))
    return -d if neg else d


class TestB59EBIRFormsParity(IntegrationTestCase):
    def test_fixtures_are_there(self):
        names = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(DATA, "*.json"))}
        for form in ("2550Q", "2551Q", "0619E", "1601EQ", "1600VT", "1701Q", "1702Q", "1701", "1701A", "1702RT"):
            self.assertIn(form, names)

    def test_every_figure_matches_ebirforms(self):
        for path in sorted(glob.glob(os.path.join(DATA, "*.json"))):
            with open(path, encoding="utf-8") as fh:
                sc = json.load(fh)
            got = ledger_figures(sc)
            name = os.path.basename(path)
            for key, expected in sc["ebirforms"].items():
                with self.subTest(fixture=name, field=key):
                    self.assertIn(key, got, f"{name}: Ledger does not write {key}")
                    self.assertEqual(number(got[key]), number(expected), f"{name}: {key} is {got[key]} in Ledger, {expected} in eBIRForms")
