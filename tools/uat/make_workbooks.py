"""Make the UAT workbooks from the case lists in tools/uat/cases/ (Sentire UAT Standard v1.0).

    python3 tools/uat/make_workbooks.py <commit> [slug ...]

Each case list module has SLUG, COVER (field label -> value; Build and Commit are filled here) and
CASES (dicts with the column A to L headers). The template is copied, never restructured: values go
into Cover column B and Test Cases columns A to L; columns M to S stay empty for the UAT runner.
"""

import importlib.util
import os
import re
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


CASE_REF = re.compile(r"LDG-[A-Z]{2}-\d{3}")


def complete_depends(m):
    """A case whose preconditions, steps or data name an earlier case of the same workbook depends
    on it: add it to Depends On, so the column never stays blank where the text names a case."""
    ids = [c["Case ID"] for c in m.CASES]
    for n, c in enumerate(m.CASES):
        have = [d.strip() for d in (c.get("Depends On") or "").split(",") if d.strip()]
        named = CASE_REF.findall(" ".join(c[k] for k in ("Preconditions", "Test Steps", "Test Data")))
        for ref in named:
            if ref in ids[:n] and ref not in have:
                have.append(ref)
        c["Depends On"] = ", ".join(sorted(set(have), key=ids.index))


def check_order(mods):
    """Every case named from another workbook belongs to a workbook that runs earlier (RUN_ORDER)."""
    from _common import RUN_ORDER

    order = {slug: i for i, (slug, _t) in enumerate(RUN_ORDER)}
    owner = {c["Case ID"]: m.SLUG for m in mods for c in m.CASES}
    for m in mods:
        for c in m.CASES:
            for ref in set(CASE_REF.findall(" ".join(c[k] for k in ("Preconditions", "Test Steps", "Test Data")))) - {c["Case ID"]}:
                other = owner.get(ref)
                assert other, f"{c['Case ID']}: names {ref}, which is in no workbook"
                assert order[other] <= order[m.SLUG], f"{c['Case ID']}: names {ref} of {other}, which runs after {m.SLUG}"


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


ROLES = ["Owner A", "Accounting Manager A", "Accountant A", "Staff A", "Accountant B"]


def master(made, commit):
    """docs/uat/UAT_MASTER_CHECKLIST.md: every workbook in run order, its task, its counts and the
    roles it signs in as. Rewritten whenever the workbooks are made."""
    from _common import RUN_ORDER

    by = {m.SLUG: (m, path, build) for m, path, build in made}
    build = next(iter(by.values()))[2]
    lines = [
        "# Sentire Ledger: full UAT checklist",
        "",
        f"Build {build} (commit {commit[:7]}). Made by tools/uat/make_workbooks.py; do not edit by hand.",
        "",
        "Run the workbooks in this order, one UAT chat per workbook (\"Run UAT for LDG-n\"), on staging restarted once before the first. "
        "Later workbooks use data the earlier ones made; never deploy to staging during the run. "
        "The role sets and what each may do: [ROLE_MATRIX.md](ROLE_MATRIX.md). How to run: [UAT_RUNNER_GUIDE.md](UAT_RUNNER_GUIDE.md).",
        "",
        "| # | Workbook | UAT task | Cases | P1 | HUMAN | " + " | ".join(ROLES) + " |",
        "| --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _ in ROLES) + " |",
    ]
    totals = [0, 0, 0] + [0] * len(ROLES)
    for n, (slug, title) in enumerate(RUN_ORDER, 1):
        if slug not in by:
            continue
        m, path, _b = by[slug]
        rel = os.path.relpath(path, os.path.join(ROOT, "docs", "uat"))
        p1 = sum(1 for c in m.CASES if c["Priority"] == "P1")
        hu = sum(1 for c in m.CASES if c["Test Steps"].startswith("HUMAN:"))
        per = [sum(1 for c in m.CASES if c["Role"] == r or r in (c["Test Steps"] + c["Preconditions"])) for r in ROLES]
        row = [len(m.CASES), p1, hu] + per
        totals = [a + b for a, b in zip(totals, row)]
        lines.append(f"| {n} | [{title}]({rel}) | {m.COVER['UAT task']} | " + " | ".join(str(x) for x in row) + " |")
    lines.append("| | **Total** | | " + " | ".join(f"**{x}**" for x in totals) + " |")
    lines += ["", "Role columns count the cases that sign in as that account (in the Role column or in the steps).", "",
              "## Every case", "", "| Case | Workbook | Priority | Role | Scenario |", "| --- | --- | --- | --- | --- |"]
    for slug, _t in RUN_ORDER:
        if slug in by:
            for c in by[slug][0].CASES:
                lines.append(f"| {c['Case ID']} | {slug} | {c['Priority']} | {c['Role']} | {c['Test Scenario'].replace('|', '/')} |")
    with open(os.path.join(ROOT, "docs", "uat", "UAT_MASTER_CHECKLIST.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    commit = subprocess.check_output(["git", "-C", ROOT, "rev-parse", sys.argv[1] if len(sys.argv) > 1 else "HEAD"], text=True).strip()
    # the branch the commit was taken from (BRANCH=main when making workbooks for a commit already on main)
    branch = os.environ.get("BRANCH") or subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    want = set(sys.argv[2:])
    made = []
    mods = [load(os.path.join(ROOT, "tools", "uat", "cases", f)) for f in sorted(os.listdir(os.path.join(ROOT, "tools", "uat", "cases")))
            if f.endswith(".py") and not f.startswith("_")]
    for m in mods:
        complete_depends(m)
    check_order(mods)
    for m in mods:
        if want and m.SLUG not in want:
            continue
        check(m)
        out = make(m, commit, branch)
        made.append((m, out[0], out[1]))
        print(*out)
    if not want:
        master(made, commit)
