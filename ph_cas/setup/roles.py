"""B69 (QA pass 4): ready role sets for client users, as Role Profiles.

ERPNext spreads master data over separate roles (a System Manager alone cannot add a supplier or
an item price), so each client user gets one of these instead of a hand-picked list:

- Owner: everything, including users and settings and approving earlier posting dates.
- Bookkeeper: books, bills, invoices, masters, stock and the BIR returns; no users or settings.
- Cashier: sales invoices, collections and stock issues at the counter; no bills, no masters.

ERPNext's Accounts User role, which collections need, also allows bills, journal entries and
suppliers. The Cashier profile therefore carries a marker role, "Cashier", and cashier_limit
(hooks.has_permission) keeps a user who has it, and no wider role, to the counter.
"""

import frappe

OWNER = "Owner"
BOOKKEEPER = "Bookkeeper"
CASHIER = "Cashier"
CASHIER_ROLE = "Cashier"
# a cashier who also holds one of these is not limited
WIDER = {"System Manager", "Accounting Manager", "Accounts Manager", "Purchase User", "Purchase Manager"}
COUNTER_LIMITED = ("Purchase Invoice", "Purchase Order", "Purchase Receipt", "Journal Entry", "Supplier", "Payment Entry")

PROFILES = {
    OWNER: [
        "System Manager", "Accounting Manager", "Accounts Manager", "Accounts User", "Sales Manager", "Sales User", "Sales Master Manager",
        "Purchase Manager", "Purchase User", "Purchase Master Manager", "Stock Manager", "Stock User", "Item Manager",
        "Manufacturing Manager", "Manufacturing User", "Projects Manager", "Projects User", "Quality Manager", "Support Team",
        "Maintenance Manager", "Maintenance User", "Auditor",
    ],
    BOOKKEEPER: [
        "Accounts Manager", "Accounts User", "Sales User", "Sales Master Manager", "Purchase User", "Purchase Master Manager",
        "Stock User", "Item Manager", "Projects User", "Auditor",
    ],
    CASHIER: [CASHIER_ROLE, "Sales User", "Accounts User", "Stock User"],
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


def setup():
    """Idempotent. Written directly rather than through Role Profile.save, whose on_update queues a
    background job and locks the record until it runs (a second migrate then fails); the profile's
    users are brought up to date here instead."""
    if not frappe.db.exists("Role", CASHIER_ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": CASHIER_ROLE, "desk_access": 1}).insert(ignore_permissions=True)
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
    """B75: the user's role set, for the home page and the counter view. A Role Profile on the
    user decides; without one, the roles do (an Accounting or System Manager is an Owner)."""
    user = user or frappe.session.user
    profiles = frappe.get_all("User Role Profile", filters={"parent": user, "parenttype": "User"}, pluck="role_profile") if frappe.db.table_exists("User Role Profile") else []
    for p in (OWNER, BOOKKEEPER, CASHIER):
        if p in profiles:
            return p
    roles = set(frappe.get_roles(user))
    if user == "Administrator" or roles & {"System Manager", "Accounting Manager"}:
        return OWNER
    if CASHIER_ROLE in roles and not roles & WIDER:
        return CASHIER
    return BOOKKEEPER
