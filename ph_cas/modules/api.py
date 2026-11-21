"""M5.2 module toggles (LDG-83 to LDG-85).

One switch per optional module on PH Modules (Sentire Ledger > Settings > Modules). Accounts, BIR
and the Home page are always on. A module that is off is hidden, not removed:

- its workspaces and sidebars leave the dock, and its links leave every other sidebar;
- its doctypes and reports leave the search bar (boot `can_read`, `can_search`, `can_create`);
- its onboarding guides and the "Complete ... Onboarding" steps that point at them disappear;
- a route to one of them shows a notice and goes Home (public/js/modules.js).

Records, roles and permissions are untouched, so switching a module back on restores everything.
Which doctypes and reports belong to a module is data (data/modules.json): every doctype and
report of the Frappe modules listed, plus `extra_*`, minus `keep_*` (shared masters such as
Customer, Supplier and Item stay visible whatever is off). Industry presets (data/presets.json)
pick the starting set.

A site whose PH Modules was never saved has everything on, so a site upgraded to this version
looks exactly as before until someone chooses.
"""

import json
import os

import frappe
from frappe import _

DOCTYPE = "PH Modules"


def _data(name: str) -> dict:
    with open(os.path.join(os.path.dirname(__file__), "data", name), encoding="utf-8") as f:
        return json.load(f)


def catalogue() -> list[dict]:
    return _data("modules.json")["modules"]


def presets() -> dict:
    return {p["industry"]: p["modules"] for p in _data("presets.json")["industries"]}


def demo_set() -> list[str]:
    return _data("presets.json")["demo"]


# ---- state ------------------------------------------------------------------------------------
def state() -> dict:
    """module key -> on (bool). Everything is on until PH Modules is saved once."""
    keys = [m["key"] for m in catalogue()]
    try:
        s = frappe.get_cached_doc(DOCTYPE)
    except Exception:
        return {k: True for k in keys}
    if not s.get("configured"):
        return {k: True for k in keys}
    return {k: bool(s.get(f"module_{k}")) for k in keys}


def modules_on() -> list[str]:
    return [k for k, on in state().items() if on]


def set_modules(on: list[str], industry: str | None = None) -> dict:
    """Turn exactly these modules on (and the rest off). Used by presets, the demo and tests."""
    s = frappe.get_doc(DOCTYPE)
    for m in catalogue():
        s.set(f"module_{m['key']}", 1 if m["key"] in on else 0)
    if industry is not None:
        s.industry = industry
    s.configured = 1
    s.flags.ignore_permissions = True
    s.save()
    return state()


@frappe.whitelist()
def apply_preset(industry: str) -> dict:
    """The starting set for an industry (ledger-site new --industry, or the Industry field)."""
    if frappe.session.user != "Administrator":
        frappe.only_for("System Manager")
    table = presets()
    if industry not in table:
        frappe.throw(_("Unknown industry {0}. Choose one of: {1}").format(industry, ", ".join(table)))
    return set_modules(table[industry], industry=industry)


def apply_demo_set():
    """The open demo starts with the common set (Accounts, Selling, Buying, BIR), once."""
    if not frappe.db.get_single_value(DOCTYPE, "configured"):
        set_modules(demo_set())


def after_change(doc):
    if not doc.configured:
        frappe.db.set_single_value(DOCTYPE, "configured", 1)
    frappe.clear_cache()  # every user's boot is rebuilt with the new menus


# ---- what is hidden -----------------------------------------------------------------------------
def hidden() -> dict:
    """Everything the switched-off modules hide, as sets of names."""
    st = state()
    off = [m for m in catalogue() if not st.get(m["key"], True)]
    # a doctype that a module which is on claims (extra_doctypes) stays visible, even when the
    # Frappe module it lives in is off: Quality Inspection sits in Stock but belongs to Quality
    claimed_by_on = set()
    for m in catalogue():
        if st.get(m["key"], True):
            claimed_by_on.update(m.get("extra_doctypes", []))
    out = {"modules": [m["key"] for m in off], "doctypes": set(), "reports": set(), "workspaces": set(),
           "sidebars": set(), "onboarding": set(), "steps": set()}
    for m in off:
        dts = set(frappe.get_all("DocType", filters={"module": ["in", m["frappe_modules"]], "istable": 0}, pluck="name"))
        dts |= set(m.get("extra_doctypes", []))
        dts -= set(m.get("keep_doctypes", []))
        out["doctypes"] |= dts
        reps = set(frappe.get_all("Report", filters={"module": ["in", m["frappe_modules"]]}, pluck="name"))
        reps |= set(m.get("extra_reports", []))
        reps -= set(m.get("keep_reports", []))
        out["reports"] |= reps
        out["workspaces"] |= set(m["workspaces"])
        out["sidebars"] |= set(m["sidebars"])
        out["onboarding"] |= set(m.get("onboarding", []))
        out["steps"] |= set(m.get("org_steps", []))
    out["doctypes"] -= claimed_by_on
    # steps of the onboarding guides that are hidden
    if out["onboarding"]:
        out["steps"] |= set(
            frappe.get_all("Onboarding Step Map", filters={"parent": ["in", list(out["onboarding"])]}, pluck="step")
        )
    return out


def _link_hidden(item: dict, h: dict) -> bool:
    lt, to = item.get("link_type"), item.get("link_to")
    return (
        (lt == "DocType" and to in h["doctypes"])
        or (lt == "Report" and to in h["reports"])
        or (lt == "Workspace" and to in h["workspaces"])
        or (lt == "Sidebar" and to in h["sidebars"])
        or (lt == "Dashboard" and to in h["workspaces"])
    )


def _prune_sidebar_items(items: list, h: dict) -> list:
    """Drop links to hidden things, then section headers left with nothing under them."""
    kept = [i for i in items if not (i.get("type") == "Link" and _link_hidden(i, h))]
    out = []
    for idx, i in enumerate(kept):
        if i.get("type") == "Section Break":
            nxt = kept[idx + 1] if idx + 1 < len(kept) else None
            if not nxt or nxt.get("type") == "Section Break":
                continue
        out.append(i)
    return out


def extend_bootinfo(bootinfo):
    if frappe.session.user == "Guest":
        return
    try:
        h = hidden()
    except Exception:
        frappe.log_error(title="Modules: could not work out the hidden modules")
        return
    bootinfo.ph_modules = {
        "on": modules_on(),
        "off": h["modules"],
        "doctypes": sorted(h["doctypes"]),
        "reports": sorted(h["reports"]),
        "workspaces": sorted(h["workspaces"]),
        "sidebars": sorted(h["sidebars"]),
        "onboarding": sorted(h["onboarding"]),
        "steps": sorted(h["steps"]),
    }
    if not h["modules"]:
        return
    prune_boot(bootinfo, h)


def prune_boot(bootinfo, h: dict, every_list: bool = False):
    """Drop from the boot what h hides: dock entries, sidebar links, workspaces, the search bar
    and "New ..." lists, and the allowed reports. every_list also clears the read, write and
    cancel lists (B82, for the Staff role set, so a hidden list opens as Not permitted)."""
    dock = bootinfo.get("dock") or {}
    if isinstance(dock, dict):
        for app, entries in dock.items():
            dock[app] = [e for e in (entries or []) if not _link_hidden(e, h)]

    # sidebars: hidden ones go, the others lose links to hidden things
    sidebars = bootinfo.get("module_sidebars") or {}
    for name in list(sidebars):
        if name in h["sidebars"]:
            sidebars.pop(name)
        elif isinstance(sidebars[name], dict) and sidebars[name].get("items"):
            sidebars[name]["items"] = _prune_sidebar_items(sidebars[name]["items"], h)

    # workspaces
    ws = bootinfo.get("workspaces")
    if isinstance(ws, dict) and isinstance(ws.get("pages"), list):
        ws["pages"] = [p for p in ws["pages"] if p.get("name") not in h["workspaces"]]
    if isinstance(bootinfo.get("allowed_workspaces"), list):
        bootinfo.allowed_workspaces = [
            w for w in bootinfo.allowed_workspaces if (w.get("name") if isinstance(w, dict) else w) not in h["workspaces"]
        ]

    # the search bar and the "New ..." lists
    user = bootinfo.get("user") or {}
    keys = ("can_read", "can_search", "can_create", "can_get_report")
    if every_list:
        keys += ("can_write", "can_submit", "can_cancel", "can_delete", "can_export", "can_import", "can_print", "can_email", "can_select")
    for key in keys:
        if isinstance(user.get(key), list):
            user[key] = [d for d in user[key] if d not in h["doctypes"]]
    if isinstance(bootinfo.get("allowed_reports"), list):
        bootinfo.allowed_reports = [r for r in bootinfo.allowed_reports if r not in h["reports"]]


@frappe.whitelist()
def status() -> dict:
    """For the Modules page: what each switch hides, in counts."""
    h = hidden()
    return {"on": modules_on(), "off": h["modules"], "doctypes": len(h["doctypes"]), "reports": len(h["reports"])}
