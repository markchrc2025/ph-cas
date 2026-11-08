import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class PHTaxRule(Document):
    def validate(self):
        if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
            frappe.throw(_("Effective to cannot be before effective from."))
        before = self.get_doc_before_save()
        if before and before.status == "confirmed" and not frappe.flags.get("ph_rule_signoff"):
            for f in ("kind", "atc", "rate", "base", "selector", "threshold", "effective_from", "effective_to"):
                if str(before.get(f)) != str(self.get(f)):
                    frappe.throw(_("A confirmed rule cannot be changed. Add a new dated rule and have it signed off."))
        if before and before.status != self.status and not frappe.flags.get("ph_rule_signoff"):
            frappe.throw(_("Status changes only through the sign-off command."))
        self.check_overlap()

    OVERLAP_KINDS = ("vat", "percentage", "ewt", "final", "compensation", "vat_withholding", "income", "discount")

    def check_overlap(self):
        """Two rate rules with the same kind, ATC, selector and base may not
        overlap in time; the resolver would then be ambiguous. Calendar,
        threshold and cap rules are looked up by id and are not checked."""
        if self.kind not in self.OVERLAP_KINDS:
            return
        others = frappe.get_all(
            "PH Tax Rule",
            filters={"kind": self.kind, "atc": self.atc or "", "selector": self.selector or "", "base": self.base or "", "name": ("!=", self.name or "")},
            fields=["name", "effective_from", "effective_to"],
        )
        a0, a1 = getdate(self.effective_from), getdate(self.effective_to) if self.effective_to else None
        for o in others:
            b0, b1 = getdate(o.effective_from), getdate(o.effective_to) if o.effective_to else None
            if (a1 is None or b0 <= a1) and (b1 is None or a0 <= b1):
                frappe.throw(_("Rule {0} overlaps {1} in time for the same kind, ATC and selector.").format(self.rule_id, o.name))

    def on_trash(self):
        if self.status == "confirmed":
            frappe.throw(_("A confirmed rule cannot be deleted."))
