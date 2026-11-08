"""B11: the tax rules table, its resolver and the sign-off check.

Rules are data (PH Tax Rule). A rule is `draft` until the CPA's sign-off file
names it. Production sites refuse to apply a draft rule; test and development
sites apply drafts so the engine can be built and tested before sign-off.
"""

import json
import os
import re

import frappe
from frappe import _
from frappe.utils import getdate

from ph_cas.controls.locks import is_production_site


class PHDraftRuleError(frappe.ValidationError):
    pass


class PHNoRuleError(frappe.ValidationError):
    pass


def parse_selector(selector: str | None) -> dict:
    out = {}
    for part in (selector or "").split(";"):
        part = part.strip()
        if not part:
            continue
        k, _, v = part.partition("=")
        out[k.strip()] = v.strip()
    return out


def _matches(rule_selector: dict, selectors: dict) -> bool:
    """Every key in the rule's selector must be present and equal in `selectors`."""
    for k, v in rule_selector.items():
        if str(selectors.get(k, "")) != v:
            return False
    return True


def candidates(kind: str, date, atc: str | None = None, base: str | None = None, **selectors) -> list[dict]:
    date = getdate(date)
    filters = {"kind": kind}
    if atc is not None:
        filters["atc"] = atc
    if base is not None:
        filters["base"] = base
    rows = frappe.get_all(
        "PH Tax Rule",
        filters=filters,
        fields=["name", "rule_id", "kind", "atc", "rate", "base", "selector", "threshold", "return_form", "return_line", "status", "effective_from", "effective_to", "legal_basis", "title"],
    )
    out = []
    for r in rows:
        if getdate(r.effective_from) > date:
            continue
        if r.effective_to and getdate(r.effective_to) < date:
            continue
        if not _matches(parse_selector(r.selector), selectors):
            continue
        r["selector_keys"] = len(parse_selector(r.selector))
        out.append(r)
    return out


def resolve(kind: str, date, atc: str | None = None, allow_draft: bool | None = None, base: str | None = None, **selectors) -> dict:
    """Exactly one rule in force on `date` for the kind, ATC and selectors.

    When several match, the most specific (most selector keys) wins; a tie is
    an error, so the seed must stay unambiguous."""
    rows = candidates(kind, date, atc, base, **selectors)
    if not rows:
        raise PHNoRuleError(
            _("No {0} rule is in force on {1} for ATC {2} and {3}.").format(kind, date, atc or "(none)", selectors or "{}")
        )
    rows.sort(key=lambda r: -r["selector_keys"])
    if len(rows) > 1 and rows[0]["selector_keys"] == rows[1]["selector_keys"]:
        raise PHNoRuleError(_("Ambiguous rules: {0} and {1} both match.").format(rows[0].rule_id, rows[1].rule_id))
    rule = rows[0]
    if allow_draft is None:
        allow_draft = not is_production_site()
    if rule.status != "confirmed" and not allow_draft:
        raise PHDraftRuleError(
            _("Rule {0} ({1}) has not been confirmed by the CPA. It cannot be applied on a production site.").format(rule.rule_id, rule.title)
        )
    return rule


def rate(kind: str, date, atc: str | None = None, **selectors) -> float:
    return float(resolve(kind, date, atc, **selectors).rate or 0)


# ---- seed ---------------------------------------------------------------


def seed_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "setup", "data", "tax_rules.json")


# Rule ids that earlier seeds carried and that were wrong; removed while still draft.
WITHDRAWN = ("GOV-EWT-GOODS", "GOV-EWT-SERVICES")


def seed():
    """Insert missing rules from the seed file as draft. Never touches existing
    rows, except withdrawn ids that are still draft."""
    for rid in WITHDRAWN:
        if frappe.db.exists("PH Tax Rule", rid) and frappe.db.get_value("PH Tax Rule", rid, "status") == "draft":
            frappe.delete_doc("PH Tax Rule", rid, ignore_permissions=True, force=True)
    with open(seed_path(), encoding="utf-8") as f:
        rows = json.load(f)
    inserted = []
    for r in rows:
        if frappe.db.exists("PH Tax Rule", r["rule_id"]):
            continue
        doc = frappe.get_doc({"doctype": "PH Tax Rule", "status": "draft", **r})
        doc.insert(ignore_permissions=True)
        inserted.append(r["rule_id"])
    return inserted


def seed_count() -> int:
    with open(seed_path(), encoding="utf-8") as f:
        return len(json.load(f))


# ---- sign-off -----------------------------------------------------------

SIGNOFF_LINE = re.compile(r"^\s*[-*]\s*(?:\[x\]\s*)?([A-Z0-9][A-Z0-9_.-]+)\b", re.IGNORECASE)


def parse_signoff(text: str) -> list[str]:
    """Rule ids listed one per line as '- RULE-ID' or '- [x] RULE-ID' under any heading."""
    ids = []
    for line in text.splitlines():
        m = SIGNOFF_LINE.match(line)
        if m:
            ids.append(m.group(1))
    return ids


def apply_signoff(path: str) -> dict:
    """Flip the rules listed in the sign-off file to confirmed. The file is
    recorded on each rule. Rules not listed are untouched."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not re.search(r"signed|sign-off|confirmed by", text, re.IGNORECASE):
        frappe.throw(_("The sign-off file must say who signed it (a line containing 'signed' or 'confirmed by')."))
    ids = parse_signoff(text)
    confirmed, missing = [], []
    frappe.flags.ph_rule_signoff = True
    try:
        for rule_id in ids:
            if not frappe.db.exists("PH Tax Rule", rule_id):
                missing.append(rule_id)
                continue
            doc = frappe.get_doc("PH Tax Rule", rule_id)
            if doc.status != "confirmed":
                doc.status = "confirmed"
                doc.signoff_file = os.path.basename(path)
                doc.save(ignore_permissions=True)
                confirmed.append(rule_id)
    finally:
        frappe.flags.ph_rule_signoff = False
    from ph_cas.audit.events import record

    record("settings_change", "PH Tax Rule", os.path.basename(path), 0, {"confirmed": confirmed, "missing": missing})
    return {"confirmed": confirmed, "missing": missing, "listed": ids}


def draft_rules() -> list[dict]:
    return frappe.get_all("PH Tax Rule", filters={"status": "draft"}, fields=["rule_id", "title", "kind", "legal_basis"], order_by="rule_id")
