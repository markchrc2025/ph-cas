"""Which chain applies to a document, and who a step's recipients are.

A chain is a PH Approval Chain (document type, company or all companies, enabled,
applies-when condition) with steps. Conditions are Python expressions on `doc`,
evaluated with frappe.safe_eval, so they can only read the document.

Module switch: PH CAS Settings.approval_chains_enabled. Off, no chain applies and
every document submits as before.
"""

import frappe
from frappe import _
from frappe.utils import cint


def module_on() -> bool:
    return bool(cint(frappe.db.get_single_value("PH CAS Settings", "approval_chains_enabled")))


def single_user_site() -> bool:
    """A site with exactly one active system user: the maker approves their own work
    (owner decision 3)."""
    n = frappe.db.count("User", {"enabled": 1, "user_type": "System User", "name": ["!=", "Guest"]})
    return n <= 1


def evaluate(condition: str | None, doc) -> bool:
    cond = (condition or "").strip()
    if not cond:
        return True
    try:
        return bool(frappe.safe_eval(cond, None, {"doc": doc.as_dict() if hasattr(doc, "as_dict") else doc}))
    except Exception as e:
        frappe.throw(_("The approval condition {0} could not be evaluated: {1}").format(cond, e))


def action_for(doc) -> str:
    """B84: a posted document (but a filed return, whose chain gates its amendment) is
    governed by its Cancel chain; anything else by its Submit chain."""
    return "Cancel" if doc.get("docstatus") == 1 and doc.doctype != "PH Tax Return" else "Submit"


def chain_for(doc, action: str | None = None):
    """The enabled chain that applies to this document, or None. A chain for the
    document's company wins over one for every company."""
    if not module_on():
        return None
    action = action or action_for(doc)
    company = doc.get("company") if hasattr(doc, "get") else None
    rows = frappe.get_all("PH Approval Chain", {"document_type": doc.doctype, "enabled": 1}, ["name", "company", "action"])
    rows = [r for r in rows if (r.action or "Submit") == action and (not r.company or r.company == company)]
    rows.sort(key=lambda r: 0 if r.company else 1)
    for r in rows:
        chain = frappe.get_doc("PH Approval Chain", r.name)  # not cached: a chain is read fresh each time
        if evaluate(chain.applies_when, doc):
            return chain
    return None


def _users_with_role(role: str) -> list[str]:
    return frappe.get_all("Has Role", {"role": role, "parenttype": "User"}, pluck="parent", distinct=True)


def _active(users) -> list[str]:
    out = []
    for u in users:
        if not u or u in ("Administrator", "Guest") or u in out:
            continue
        if frappe.db.get_value("User", u, "enabled"):
            out.append(u)
    return out


def _dynamic(step, doc) -> list[str]:
    value = doc.get(step.dynamic_field) if hasattr(doc, "get") else None
    if not value:
        return []
    if step.use_lookup:
        hit = frappe.db.get_value("PH Approval Lookup", {"document_type": doc.doctype, "field": step.dynamic_field, "value": str(value)}, "approver")
        return [hit] if hit else []
    if frappe.db.exists("User", value):
        return [value]
    if frappe.db.exists("Employee", value):
        boss = frappe.db.get_value("Employee", value, "reports_to")
        user = frappe.db.get_value("Employee", boss, "user_id") if boss else None
        return [user] if user else []
    return []


def recipients(step, doc) -> list[str]:
    """The active users a step goes to, in a stable order."""
    t = step.recipient_type
    if t == "Role":
        users = _users_with_role(step.role)
    elif t == "User":
        users = [step.user]
    elif t == "Group":
        users = frappe.get_all("PH Approval Group User", {"parent": step.group}, pluck="user", order_by="idx")
    else:
        users = _dynamic(step, doc)
    users = _active(sorted(users) if t == "Role" else users)
    return users


def snapshot(chain) -> list[dict]:
    """The steps as they are now, kept on the request so a later edit of the chain
    does not change a running one."""
    return [
        {
            "step": cint(s.step),
            "title": s.title,
            "condition": s.condition or "",
            "recipient_type": s.recipient_type,
            "role": s.role,
            "user": s.user,
            "group": s.group,
            "dynamic_field": s.dynamic_field,
            "use_lookup": cint(s.use_lookup),
            "receiving_order": s.receiving_order or "Any one",
            "role_type": s.role_type or "Approver",
            "allow_self_approval": cint(s.allow_self_approval),
            "private_note": s.private_note or "",
        }
        for s in sorted(chain.steps, key=lambda s: (cint(s.step), s.idx))
    ]


TEMPLATES = {
    "manager_above_amount": {
        "title": "Manager approves above an amount",
        "applies_when": "doc.grand_total > 50000",
        "steps": [{"step": 1, "title": "Accounts manager", "recipient_type": "Role", "role": "Accounts Manager", "receiving_order": "Any one", "role_type": "Approver"}],
    },
    "supervisor_then_manager": {
        "title": "Supervisor, then manager by amount band",
        "applies_when": "",
        "steps": [
            {"step": 1, "title": "Supervisor (up to 50,000)", "recipient_type": "Role", "role": "Accounts User", "receiving_order": "Any one", "role_type": "Approver", "condition": "doc.grand_total <= 50000"},
            {"step": 2, "title": "Accounts manager (over 50,000)", "recipient_type": "Role", "role": "Accounts Manager", "receiving_order": "Any one", "role_type": "Approver", "condition": "doc.grand_total > 50000"},
        ],
    },
    "everyone_in_group": {
        "title": "Everyone in a group",
        "applies_when": "",
        "steps": [{"step": 1, "title": "The approvers", "recipient_type": "Group", "group": "", "receiving_order": "Everyone", "role_type": "Approver"}],
    },
}


def from_template(key: str, document_type: str, company: str | None = None, group: str | None = None):
    """A new, disabled chain from a template, for the owner to finish and switch on."""
    t = TEMPLATES[key]
    doc = frappe.new_doc("PH Approval Chain")
    doc.title = f"{t['title']} ({document_type})"
    doc.document_type = document_type
    doc.company = company
    doc.enabled = 0
    doc.applies_when = t["applies_when"]
    for s in t["steps"]:
        row = dict(s)
        if row.get("recipient_type") == "Group":
            row["group"] = group or row.get("group")
        doc.append("steps", row)
    doc.insert()
    return doc


def install_demo(company: str):
    """The demo site's chains (plan 2.5): Journal Entry and Purchase Order above
    50,000 go to the accounts manager. Switches the module on for the demo."""
    for doctype in ("Journal Entry", "Purchase Order"):
        if frappe.db.exists("PH Approval Chain", {"document_type": doctype, "company": company}):
            continue
        doc = from_template("manager_above_amount", doctype, company)
        doc.applies_when = "doc.total_debit > 50000" if doctype == "Journal Entry" else "doc.grand_total > 50000"
        doc.enabled = 1
        doc.save(ignore_permissions=True)
    frappe.db.set_single_value("PH CAS Settings", "approval_chains_enabled", 1)


def extend_bootinfo(bootinfo):
    """B88: the document types an enabled chain covers, with its actions, so a form can hold
    Submit or Cancel until it knows whether approval is needed."""
    out = {}
    if module_on():
        for r in frappe.get_all("PH Approval Chain", {"enabled": 1}, ["document_type", "action"]):
            out.setdefault(r.document_type, [])
            act = r.action or "Submit"
            if act not in out[r.document_type]:
                out[r.document_type].append(act)
    bootinfo.ph_cas_chain_doctypes = out
