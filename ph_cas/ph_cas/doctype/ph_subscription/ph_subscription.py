"""B35: the provider's record of one client subscription (kept on MCRC's own site)."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from ph_cas.hosting.tiers import TIERS


class PHSubscription(Document):
    def validate(self):
        self.site = (self.site or "").strip().lower()
        if not self.site or " " in self.site:
            frappe.throw(_("Site must be a hostname such as acme.ledger.sentire.solutions"))
        defaults = TIERS.get(self.tier, {})
        for k, v in defaults.items():
            if self.get(k) in (None, ""):
                self.set(k, v)
        if self.status == "Pilot" and not self.pilot_until:
            frappe.throw(_("A pilot needs a Pilot until date"))
        if self.status == "Active" and not self.paid_until:
            frappe.throw(_("An active subscription needs a Paid until date"))
        if self.status == "Notice given" and not (self.notice_received_on and self.service_ends_on):
            frappe.throw(_("Notice given needs Notice received and Service ends dates"))
        if self.status == "Ended" and not self.export_delivered_on:
            frappe.throw(_("Ended needs the Export delivered date (docs/runbooks/offboarding.md)"))
        if self.tier == "Enterprise" and self.hosting != "Dedicated pair (Enterprise)":
            self.hosting = "Dedicated pair (Enterprise)"
        self.set_tier_command = self.command()
        self.modules_on = modules_from_usage(self.usage_json)

    def command(self) -> str:
        parts = [f"ledger-site set-tier {self.site} {self.tier}"]
        if self.paid_until:
            parts.append(f"--until {self.paid_until}")
        for flag, field in (("--max-users", "max_users"), ("--max-branches", "max_branches"), ("--max-companies", "max_companies"), ("--invoices", "monthly_invoice_limit")):
            if self.get(field) not in (None, "") and int(self.get(field)) != TIERS.get(self.tier, {}).get(field):
                parts.append(f"{flag} {int(self.get(field))}")
        return " ".join(parts)

    def is_due(self) -> bool:
        return bool(self.paid_until and getdate(self.paid_until) < getdate(today()) and self.status == "Active")


def due_subscriptions() -> list[str]:
    return [
        s.name
        for s in frappe.get_all("PH Subscription", filters={"status": "Active"}, fields=["name", "paid_until"])
        if s.paid_until and getdate(s.paid_until) < getdate(today())
    ]


def modules_from_usage(usage_json: str | None) -> str | None:
    """The modules list of a usage report (ledger-site usage), as one readable line (LDG-85)."""
    import json

    try:
        mods = json.loads(usage_json or "{}").get("modules_on")
    except (ValueError, AttributeError):
        return None
    if not isinstance(mods, list):
        return None
    return ", ".join(m.capitalize() if m != "crm" else "CRM" for m in mods) or "None (Accounts and BIR only)"

