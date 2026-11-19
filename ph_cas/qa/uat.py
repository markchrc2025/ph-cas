"""B77 (Sentire UAT Standard v1.0): what a separate UAT session needs on staging.

- The build stamp, readable without signing in (build_info), so the tester can match it to the
  workbook's Cover.
- UAT accounts, seeded with the staging site and kept in its snapshot: Owner, Bookkeeper and
  Cashier for Company A (the demo company), the Owner and Bookkeeper also for Companies C and D
  (fresh companies for go-live and for imports), and a Bookkeeper for Company B, the other tenant. User
  Permissions keep each to its companies, so "Company B cannot open Company A's record" is
  testable. The password is STAGING_UAT_PASSWORD (Dokploy); it is never written anywhere else.
  The addresses are plus-addresses of the test mailbox.
- Outgoing mail on staging goes only to the test mailbox, whoever it was addressed to.
"""

from __future__ import annotations

import os

import frappe
from frappe import _

TEST_MAILBOX = "mcrc.business.solutions@gmail.com"
COMPANY_A = "Tala Trading Corporation"
COMPANY_B = "UAT Company B Corp."
COMPANY_C = "UAT Bagong Simula Corp."  # fresh: go-live
COMPANY_D = "UAT Bagong Bukas Corp."  # fresh: imports


def _plus(tag: str) -> str:
    local, domain = mailbox().split("@")
    return f"{local}+{tag}@{domain}"


def mailbox() -> str:
    return os.environ.get("STAGING_TEST_MAILBOX") or TEST_MAILBOX


def accounts() -> list[dict]:
    return [
        {"email": _plus("uat-owner-a"), "first_name": "UAT Owner", "last_name": "A", "profile": "Owner", "companies": [COMPANY_A, COMPANY_C, COMPANY_D]},
        {"email": _plus("uat-bookkeeper-a"), "first_name": "UAT Bookkeeper", "last_name": "A", "profile": "Bookkeeper", "companies": [COMPANY_A, COMPANY_C, COMPANY_D]},
        {"email": _plus("uat-cashier-a"), "first_name": "UAT Cashier", "last_name": "A", "profile": "Cashier", "companies": [COMPANY_A]},
        {"email": _plus("uat-bookkeeper-b"), "first_name": "UAT Bookkeeper", "last_name": "B", "profile": "Bookkeeper", "companies": [COMPANY_B]},
    ]


@frappe.whitelist(allow_guest=True)
def build_info() -> dict:
    from ph_cas import buildstamp

    return {"product": "Sentire Ledger", "version": buildstamp.version(), "build": buildstamp.build()}


def _company(name, abbr, tin, method="Periodic"):
    from ph_cas.qa.fullpass import _trading_company

    if not frappe.db.exists("Company", name):
        _trading_company(name, abbr, method, tin)
    return name


def seed_uat():
    """Called from ph_cas.qa.api.seed on the staging site's first start (and safe to run again)."""
    from ph_cas.qa.api import require_staging
    from ph_cas.setup import roles

    require_staging()
    frappe.set_user("Administrator")
    _company(COMPANY_B, "UATB", "000-905-201")
    _company(COMPANY_C, "UATC", "000-905-202")
    _company(COMPANY_D, "UATD", "000-905-203")
    roles.setup()
    password = os.environ.get("STAGING_UAT_PASSWORD")
    for a in accounts():
        if not frappe.db.exists("User", a["email"]):
            frappe.get_doc({"doctype": "User", "email": a["email"], "first_name": a["first_name"], "last_name": a["last_name"],
                            "send_welcome_email": 0, "user_type": "System User", "role_profiles": [{"role_profile": a["profile"]}]}).insert(ignore_permissions=True)
        u = frappe.get_doc("User", a["email"])
        u.enabled = 1
        u.flags.ignore_permissions = True
        u.save()
        have = set(frappe.get_all("User Permission", filters={"user": a["email"], "allow": "Company"}, pluck="for_value"))
        for c in a["companies"]:
            if c not in have and frappe.db.exists("Company", c):
                frappe.get_doc({"doctype": "User Permission", "user": a["email"], "allow": "Company", "for_value": c, "apply_to_all_doctypes": 1,
                                "is_default": 1 if c == a["companies"][0] else 0}).insert(ignore_permissions=True)
        if password:
            from frappe.utils.password import update_password

            update_password(a["email"], password)
    frappe.db.commit()
    return [a["email"] for a in accounts()]


@frappe.whitelist()
def check_accounts() -> list[dict]:
    """Definition of Ready: each UAT account exists, is enabled, has its role set and companies, and
    signs in with STAGING_UAT_PASSWORD. Reports yes or no; never shows the password."""
    from frappe.utils.password import check_password

    from ph_cas.qa.api import require_staging
    from ph_cas.setup.roles import role_set

    require_staging()
    frappe.only_for("System Manager")
    password = os.environ.get("STAGING_UAT_PASSWORD")
    out = []
    for a in accounts():
        row = {"user": a["email"], "exists": bool(frappe.db.exists("User", a["email"]))}
        if row["exists"]:
            row["enabled"] = bool(frappe.db.get_value("User", a["email"], "enabled"))
            row["role_set"] = role_set(a["email"])
            row["companies"] = sorted(frappe.get_all("User Permission", filters={"user": a["email"], "allow": "Company"}, pluck="for_value"))
            try:
                check_password(a["email"], password or "", delete_tracker_cache=False)
                row["signs_in"] = True
            except Exception:
                row["signs_in"] = False
        out.append(row)
    return out


def redirect_staging_mail(doc, method=None):
    """Email Queue before_insert: on staging every mail goes to the test mailbox only."""
    from ph_cas.qa.api import is_staging

    if not is_staging():
        return
    box = mailbox()
    for r in doc.get("recipients") or []:
        r.recipient = box
    if doc.get("show_as_cc"):
        doc.show_as_cc = ""
