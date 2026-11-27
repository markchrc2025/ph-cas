"""Cover fields shared by every Ledger workbook (Sentire UAT Standard v1.0)."""

ACCOUNTS = """Owner A: mcrc.business.solutions+uat-owner-a@gmail.com (role set Owner; Companies A, C, D)
Accounting Manager A: mcrc.business.solutions+uat-acctmgr-a@gmail.com (role set Accounting Manager; Companies A, C, D)
Accountant A: mcrc.business.solutions+uat-accountant-a@gmail.com (role set Accountant; Companies A, C, D)
Staff A: mcrc.business.solutions+uat-staff-a@gmail.com (role set Staff; Company A)
Accountant B: mcrc.business.solutions+uat-accountant-b@gmail.com (role set Accountant; Company B)
Passwords: STAGING_UAT_PASSWORD in the Ledger Staging app's Environment tab (Dokploy); seeded by ph_cas/qa/uat.py. Two-factor sign-in is off on staging."""

TENANTS = """Company A: Tala Trading Corporation (VAT, has history)
Company B: UAT Company B Corp. (the other tenant; Accountant B only)
Company C: UAT Bagong Simula Corp. (fresh, for go-live)
Company D: UAT Bagong Bukas Corp. (fresh, for imports)"""


PREPARED_BY = "Claude Code (B79 session), 2026-11-20; corrected for the retest (B82), 2026-11-21"
ROLE_MATRIX = "docs/uat/ROLE_MATRIX.md"


def cover(process, task, out_of_scope, settings="None beyond the staging defaults (every module on, two-factor off).", known="None", setup=None):
    return {
        "Product": "Sentire Ledger",
        "Project key": "LDG",
        "Process": process,
        "Environment": "staging",
        "App URL": "https://ledger-staging.apps.sentire.solutions",
        "Where the build shows": "Help > Your plan (last line) and Help > Get help (details box); also https://ledger-staging.apps.sentire.solutions/api/method/ph_cas.qa.uat.build_info",
        "Test accounts": ACCOUNTS,
        "Tenants": TENANTS,
        "Test mailbox": "mcrc.business.solutions@gmail.com (every staging mail goes there; also listed under Email Queue)",
        "Test data setup": setup or "Staging restarted in Dokploy before handoff (restores the QA snapshot with the UAT accounts and Companies A to D); time in the UAT task's handoff block. Do not deploy during the run.",
        "Feature flags and settings": settings,
        "Out of scope": out_of_scope,
        "Known issues": known,
        "UAT task": task,
        "Prepared by": PREPARED_BY,
    }


TODAY = "today's date (the date the run starts), written below as T; the day before is T-1"


URL = "https://ledger-staging.apps.sentire.solutions"
REFUSED = ("a \"Not Permitted\" message or page (\"You need the '{p}' permission on {dt} ...\" or \"No permission for {dt}\"), "
           "or, on a new form, the orange note \"Your role cannot add new {label} records. Nothing here will be saved. Ask an Accounting Manager or the Owner.\" with no Save button; nothing is saved")
# B82: the names the app shows for its own doctypes (ph_cas/translations/en.csv)
LABELS = {"PH Approval Chain": "Approval Chain", "PH 2307 Issued": "2307 Issued", "PH Tax Return": "BIR Return", "PH Modules": "Modules", "PH CAS Settings": "Sentire Ledger Settings"}


def refused(dt, p="create"):
    return REFUSED.format(dt=dt, p=p, label=LABELS.get(dt, dt))


def case(cid, module, issue, scenario, role, pre, steps, data, expected, prio, dep="", side="None"):
    """One row, columns A to L, in the template's header names."""
    join = lambda x: "\n".join(f"{i}. {s}" for i, s in enumerate(x, 1)) if isinstance(x, (list, tuple)) else x
    return {"Case ID": cid, "Module": module, "Linked Issue": issue, "Test Scenario": scenario, "Role": role, "Preconditions": pre,
            "Test Steps": join(steps), "Test Data": data, "Expected Result": join(expected), "Priority": prio, "Depends On": dep, "Side Effects": side}


# The order a UAT session runs the workbooks in: later workbooks use data the earlier ones made.
RUN_ORDER = [
    ("setup-company", "Company setup and modules"),
    ("paid-now-card-counter", "Paid in full now, credit card and counter views"),
    ("record-expense", "Record an expense"),
    ("roles-permissions", "Roles and permissions"),
    ("role-homes", "Role homes, counter view and Help menu"),
    ("reports-page", "Reports page"),
    ("sales-collections", "Sales and collections"),
    ("masters-stock", "Masters and stock"),
    ("purchases-payables", "Purchases and payables"),
    ("approvals", "Approvals"),
    ("journals-periods", "Journals and periods"),
    ("bir-returns", "BIR returns"),
    ("books-audit", "Books and audit"),
    ("ledgers-cash-position", "Subsidiary ledgers and cash position"),
    ("import-templates", "Import templates and batch edit"),
    ("go-live", "Go-live and opening balances"),
    ("paper-check-pack", "Print pack for the paper check"),
    ("framework-branding", "Sentire Framework branding"),
    ("get-to-know", "Get to know Sentire Ledger checklist"),
    ("plan-and-settings", "Plan and settings"),
]
