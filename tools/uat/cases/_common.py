"""Cover fields shared by every Ledger workbook (Sentire UAT Standard v1.0)."""

ACCOUNTS = """Owner A: mcrc.business.solutions+uat-owner-a@gmail.com (Companies A, C, D)
Bookkeeper A: mcrc.business.solutions+uat-bookkeeper-a@gmail.com (Companies A, C, D)
Cashier A: mcrc.business.solutions+uat-cashier-a@gmail.com (Company A)
Bookkeeper B: mcrc.business.solutions+uat-bookkeeper-b@gmail.com (Company B)
Passwords: STAGING_UAT_PASSWORD in the Ledger Staging app's Environment tab (Dokploy); seeded by ph_cas/qa/uat.py. Two-factor sign-in is off on staging."""

TENANTS = """Company A: Tala Trading Corporation (VAT, has history)
Company B: UAT Company B Corp. (the other tenant; Bookkeeper B only)
Company C: UAT Bagong Simula Corp. (fresh, for go-live)
Company D: UAT Bagong Bukas Corp. (fresh, for imports)"""


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
        "Prepared by": "Claude Code (B77 session), 2026-11-19",
    }


TODAY = "today's date (the date the run starts), written below as T; the day before is T-1"
