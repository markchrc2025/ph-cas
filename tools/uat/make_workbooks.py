"""Make the UAT workbooks from the case lists in tools/uat/cases/ (Sentire UAT Standard v1.0).

    python3 tools/uat/make_workbooks.py <commit> [slug ...]

Each case list module has SLUG, COVER (field label -> value; Build and Commit are filled here) and
CASES (dicts with the column A to L headers). The template is copied, never restructured: values go
into Cover column B and Test Cases columns A to L; columns M to S stay empty for the UAT runner.
"""

import importlib.util
import os
import shutil
import subprocess
import sys

from openpyxl import load_workbook
from openpyxl.styles import Alignment

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "uat", "cases"))
TEMPLATE = os.path.join(ROOT, "docs", "uat", "UAT_TEMPLATE.xlsx")
HEADERS = ["Case ID", "Module", "Linked Issue", "Test Scenario", "Role", "Preconditions", "Test Steps", "Test Data", "Expected Result",
           "Priority", "Depends On", "Side Effects"]


def build_of(commit):
    return subprocess.check_output([sys.executable, os.path.join(ROOT, "ph_cas", "buildstamp.py"), "--git", commit], text=True).strip()


def load(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check(m):
    ids = [c["Case ID"] for c in m.CASES]
    assert len(ids) == len(set(ids)), f"{m.SLUG}: duplicate case IDs"
    assert len(ids) <= 40, f"{m.SLUG}: more than 40 cases"
    for c in m.CASES:
        missing = [h for h in HEADERS if h not in c and h not in ("Depends On",)]
        assert not missing, f"{c['Case ID']}: missing {missing}"
        assert c["Priority"] in ("P1", "P2", "P3"), c["Case ID"]
        for d in (c.get("Depends On") or "").split(","):
            assert not d.strip() or d.strip() in ids[: ids.index(c["Case ID"])], f"{c['Case ID']}: depends on {d} which is not before it"
        assert "password" not in (c["Test Data"] + c["Test Steps"]).lower() or "STAGING_UAT_PASSWORD" in c["Test Data"] + c["Test Steps"], c["Case ID"]


def make(m, commit, branch):
    build = build_of(commit)
    folder = os.path.join(ROOT, "docs", "uat", m.SLUG)
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        if old.startswith("UAT_") and old.endswith(".xlsx"):
            os.remove(os.path.join(folder, old))
    path = os.path.join(folder, f"UAT_LDG_{m.SLUG}_{build}.xlsx")
    shutil.copy(TEMPLATE, path)
    wb = load_workbook(path)
    cover = wb["Cover"]
    values = dict(m.COVER, **{"Build": build, "Commit": f"{branch} @ {commit[:7]}"})
    seen = set()
    for row in cover.iter_rows(min_row=1):
        label = row[0].value
        if label in values:
            row[1].value = values[label]
            row[1].alignment = Alignment(wrap_text=True, vertical="top")
            seen.add(label)
    assert seen == set(values), f"Cover fields not found: {set(values) - seen}"
    ws = wb["Test Cases"]
    head = [c.value for c in ws[1]]
    assert head[:12] == HEADERS, head
    for i, case in enumerate(m.CASES, start=2):
        for j, h in enumerate(HEADERS, start=1):
            cell = ws.cell(row=i, column=j)
            cell.value = case.get(h) or None
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)
    return path, build, len(m.CASES), sum(1 for c in m.CASES if c["Priority"] == "P1"), sum(1 for c in m.CASES if c["Test Steps"].startswith("HUMAN:"))


if __name__ == "__main__":
    commit = subprocess.check_output(["git", "-C", ROOT, "rev-parse", sys.argv[1] if len(sys.argv) > 1 else "HEAD"], text=True).strip()
    branch = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    want = set(sys.argv[2:])
    for f in sorted(os.listdir(os.path.join(ROOT, "tools", "uat", "cases"))):
        if not f.endswith(".py") or f.startswith("_"):
            continue
        m = load(os.path.join(ROOT, "tools", "uat", "cases", f))
        if want and m.SLUG not in want:
            continue
        check(m)
        print(*make(m, commit, branch))
