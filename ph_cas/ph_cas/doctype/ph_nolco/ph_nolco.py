import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PHNOLCO(Document):
    def validate(self):
        from ph_cas.tax.rules import resolve

        if self.loss_year in (2020, 2021):
            rule = resolve("cap", f"{self.loss_year}-12-31", base="nolco_years", loss_year="2020-2021")
        else:
            rule = resolve("cap", f"{self.loss_year}-12-31", base="nolco_years")
        self.carry_years = int(rule.threshold)
        self.expiry_year = self.loss_year + self.carry_years
        self.used = flt(self.used)
        self.balance = flt(self.amount) - self.used
        if self.balance < 0:
            frappe.throw(_("Used cannot exceed the loss."))
