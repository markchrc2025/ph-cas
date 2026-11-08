import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime


def period_label(form: str, start, end) -> str:
    s, e = getdate(start), getdate(end)
    if form in ("0619-E", "1600-VT"):
        return f"{s.year}-{s.month:02d}"
    if form in ("1604-E", "1701", "1701A", "1702-RT"):
        return f"{s.year}"
    return f"{s.year}-Q{(s.month - 1) // 3 + 1}"


class PHTaxReturnFigures(Document):
    def autoname(self):
        self.period_label = period_label(self.form, self.period_start, self.period_end)
        self.company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        self.name = f"{self.form}-{self.period_label}-{self.company_abbr}"

    def validate(self):
        if getdate(self.period_end) < getdate(self.period_start):
            frappe.throw(_("Period end cannot be before period start."))
        self.period_label = period_label(self.form, self.period_start, self.period_end)
        self.company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        for row in self.adjustments:
            row.source = "typed"
            if not (row.reason or "").strip():
                frappe.throw(_("Adjustment to item {0} needs a reason.").format(row.item))
        before = self.get_doc_before_save()
        if before and before.filed and not frappe.flags.get("ph_recompute_filed"):
            if [(r.item, flt(r.amount)) for r in before.lines] != [(r.item, flt(r.amount)) for r in self.lines]:
                frappe.throw(_("The figures of a filed return cannot change. Compute an amended return instead."))

    def compute(self):
        from ph_cas.tax import returns

        fn = returns.COMPUTES.get(self.form)
        if not fn:
            frappe.throw(_("No compute exists for {0} yet.").format(self.form))
        lines = fn(self.company, self.period_start, self.period_end)
        self.set("lines", [])
        for item, label, amount, source in lines:
            self.append("lines", {"item": item, "label": label, "amount": flt(amount, 2), "source": source})
        self.computed_on = now_datetime()
        self.computed_by = frappe.session.user
        return self

    def figure(self, item: str) -> float:
        total = sum(flt(r.amount) for r in self.lines if r.item == item)
        total += sum(flt(r.amount) for r in self.adjustments if r.item == item)
        return flt(total, 2)

    @frappe.whitelist()
    def recompute(self):
        if self.filed:
            frappe.throw(_("This return is marked filed. Compute an amended return as a new record."))
        self.compute()
        self.save()
        return {"lines": len(self.lines)}
