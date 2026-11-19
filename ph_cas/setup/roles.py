"""B69 (QA pass 4), B79 (four role sets): ready role sets for client users, as Role Profiles.

ERPNext spreads master data over separate roles (a System Manager alone cannot add a supplier or
an item price), so each client user gets one of these instead of a hand-picked list:

- Owner: everything, including users, modules and settings.
- Accounting Manager: everything in the books except users, modules and system settings: the
  chart of accounts, fiscal years and tax templates, earlier posting dates, accounting periods
  and stock counts, approvals, finalising BIR returns and the paper-check pack.
- Accountant (was Bookkeeper): records the business: invoices, bills, payments, journal entries,
  customers, suppliers, items, stock moves and BIR return drafts; reads every report. Cannot
  change the chart, post to an earlier date, close a period, approve or finalise a return.
- Staff (was Cashier): sales invoices, collections and stock issues at the counter; no bills,
  no journal entries, no suppliers.

ERPNext's Accounts User role, which collections need, also allows bills, journal entries and
suppliers. The Staff profile therefore carries a marker role, "Cashier", and cashier_limit
(hooks.has_permission) keeps a user who has it, and no wider role, to the counter.
The full matrix, as UAT checks it, is docs/uat/ROLE_MATRIX.md.
"""

import frappe

OWNER = "Owner"
ACCOUNTING_MANAGER = "Accounting Manager"
ACCOUNTANT = "Accountant"
STAFF = "Staff"
ROLE_SETS = (OWNER, ACCOUNTING_MANAGER, ACCOUNTANT, STAFF)
# B79 renamed two role sets; the old names stay as aliases for older code and the rename patch
BOOKKEEPER = ACCOUNTANT
CASHIER = STAFF
RENAMED = {"Bookkeeper": ACCOUNTANT, "Cashier": STAFF}
CASHIER_ROLE = "Cashier"  # the counter marker role carried by the Staff set
# a cashier who also holds one of these is not limited
WIDER = {"System Manager", "Accounting Manager", "Accounts Manager", "Purchase User", "Purchase Manager"}
COUNTER_LIMITED = ("Purchase Invoice", "Purchase Order", "Purchase Receipt", "Journal Entry", "Supplier", "Payment Entry",
                   "PH Tax Return", "PH 2307 Issued", "PH Alphalist File")  # B79: the BIR returns too

PROFILES = {
    OWNER: [
        "System Manager", "Accounting Manager", "Accounts Manager", "Accounts User", "Sales Manager", "Sales User", "Sales Master Manager",
        "Purchase Manager", "Purchase User", "Purchase Master Manager", "Stock Manager", "Stock User", "Item Manager",
        "Manufacturing Manager", "Manufacturing User", "Projects Manager", "Projects User", "Quality Manager", "Support Team",
        "Maintenance Manager", "Maintenance User", "Auditor",
    ],
    ACCOUNTING_MANAGER: [
        "Accounting Manager", "Accounts Manager", "Accounts User", "Sales Manager", "Sales User", "Sales Master Manager",
        "Purchase Manager", "Purchase User", "Purchase Master Manager", "Stock Manager", "Stock User", "Item Manager",
        "Projects User", "Auditor",
    ],
    ACCOUNTANT: [
        "Accounts User", "Sales User", "Sales Master Manager", "Purchase User", "Purchase Master Manager",
        "Stock User", "Item Manager", "Projects User", "Auditor",
    ],
    STAFF: [CASHIER_ROLE, "Sales User", "Accounts User", "Stock User"],
}


def cashier_limit(doc, ptype=None, user=None, debug=False):
    """hooks.has_permission for COUNTER_LIMITED: a cashier reads them but does not make them,
    except a collection (Payment Entry of type Receive)."""
    if ptype in (None, "read", "report", "export", "print", "email", "select", "share"):
        return True
    roles = set(frappe.get_roles(user))
    if CASHIER_ROLE not in roles or roles & WIDER:
        return True
    doctype = doc if isinstance(doc, str) else doc.doctype
    if doctype == "Payment Entry" and not isinstance(doc, str) and (doc.get("payment_type") or "Receive") == "Receive":
        return True
    return False


def _rename_old_profiles():
    """B79: Bookkeeper -> Accountant, Cashier -> Staff. The users who hold them follow."""
    for old, new in RENAMED.items():
        if not frappe.db.exists("Role Profile", old):
            continue
        if frappe.db.exists("Role Profile", new):
            frappe.db.sql("update `tabUser Role Profile` set role_profile=%s where role_profile=%s", (new, old))
            frappe.db.delete("Has Role", {"parenttype": "Role Profile", "parent": old})
            frappe.db.delete("Role Profile", {"name": old})
        else:
            frappe.rename_doc("Role Profile", old, new, force=True, show_alert=False)
            frappe.db.set_value("Role Profile", new, "role_profile", new, update_modified=False)
        if frappe.db.has_column("User", "role_profile_name"):
            frappe.db.sql("update `tabUser` set role_profile_name=%s where role_profile_name=%s", (new, old))


def setup():
    """Idempotent. Written directly rather than through Role Profile.save, whose on_update queues a
    background job and locks the record until it runs (a second migrate then fails); the profile's
    users are brought up to date here instead."""
    if not frappe.db.exists("Role", CASHIER_ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": CASHIER_ROLE, "desk_access": 1}).insert(ignore_permissions=True)
    _rename_old_profiles()
    for name, roles in PROFILES.items():
        roles = [r for r in roles if frappe.db.exists("Role", r)]
        if frappe.db.exists("Role Profile", name):
            have = frappe.get_all("Has Role", filters={"parenttype": "Role Profile", "parent": name}, pluck="role")
            if sorted(have) == sorted(roles):
                continue
            frappe.db.delete("Has Role", {"parenttype": "Role Profile", "parent": name})
        else:
            doc = frappe.new_doc("Role Profile")
            doc.role_profile = doc.name = name
            doc.db_insert()
        for i, r in enumerate(roles, 1):
            row = frappe.new_doc("Has Role")
            row.update({"parenttype": "Role Profile", "parentfield": "roles", "parent": name, "role": r, "idx": i})
            row.db_insert()
        frappe.clear_cache(doctype="Role Profile")
        for user in frappe.get_all("User Role Profile", filters={"role_profile": name}, pluck="parent"):
            u = frappe.get_doc("User", user)
            u.flags.ignore_permissions = True
            u.save()  # a save re-applies the profile's roles


def role_set(user: str | None = None) -> str:
    """B75/B79: the user's role set, for the home page and the counter view. A Role Profile on the
    user decides; without one, the roles do (a System Manager is an Owner)."""
    user = user or frappe.session.user
    profiles = frappe.get_all("User Role Profile", filters={"parent": user, "parenttype": "User"}, pluck="role_profile") if frappe.db.table_exists("User Role Profile") else []
    profiles = [RENAMED.get(p, p) for p in profiles]
    for p in ROLE_SETS:
        if p in profiles:
            return p
    roles = set(frappe.get_roles(user))
    if user == "Administrator" or "System Manager" in roles:
        return OWNER
    if "Accounting Manager" in roles:
        return ACCOUNTING_MANAGER
    if CASHIER_ROLE in roles and not roles & WIDER:
        return STAFF
    return ACCOUNTANT


# B79: Staff (the counter) runs the counter's reports only. The Accounts User role that
# collections need would otherwise open every accounting report, the financial statements included.
STAFF_REPORTS = {
    "PH Cash Position", "Sales Register", "Item-wise Sales Register", "Accounts Receivable", "Accounts Receivable Summary",
    "Stock Balance", "Stock Projected Qty",
}


def counter_limited(user: str | None = None) -> bool:
    roles = set(frappe.get_roles(user or frappe.session.user))
    return CASHIER_ROLE in roles and not roles & WIDER


def check_report(report_name: str):
    if counter_limited() and report_name not in STAFF_REPORTS:
        frappe.throw(frappe._("Staff users can open the counter's reports only. Ask an accountant for {0}.").format(report_name), frappe.PermissionError)


@frappe.whitelist()
@frappe.read_only()
def run_report(report_name: str, **kwargs):
    """Overrides frappe.desk.query_report.run (hooks.override_whitelisted_methods)."""
    from frappe.desk.query_report import run

    check_report(report_name)
    return run(report_name, **kwargs)


@frappe.whitelist()
def export_report():
    """Overrides frappe.desk.query_report.export_query."""
    from frappe.desk.query_report import export_query

    check_report(frappe.form_dict.get("report_name") or "")
    return export_query()


CHART_ROLES = {"System Manager", "Accounting Manager", "Accounts Manager"}


def chart_limit(doc, ptype=None, user=None, debug=False):
    """hooks.has_permission for Account and Cost Center: ERPNext lets Accounts User add and change
    accounts; in Ledger the chart belongs to the Owner and the Accounting Manager (B79)."""
    if ptype in (None, "read", "report", "export", "print", "email", "select", "share"):
        return True
    return bool(set(frappe.get_roles(user)) & CHART_ROLES)
