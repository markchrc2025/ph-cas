import frappe
from frappe import _
from frappe.model.document import Document


class PHAccountMapping(Document):
    def validate(self):
        from ph_cas.setup.chart import PURPOSES

        if self.purpose not in PURPOSES:
            frappe.throw(_("Unknown purpose {0}.").format(self.purpose))
        self.description = PURPOSES[self.purpose]["description"]
        acc = frappe.db.get_value("Account", self.account, ["company", "is_group", "root_type"], as_dict=True)
        if not acc or acc.company != self.company:
            frappe.throw(_("The account must belong to {0}.").format(self.company))
        if acc.is_group:
            frappe.throw(_("A group account cannot receive postings."))
        want = PURPOSES[self.purpose]["root_type"]
        if acc.root_type != want:
            frappe.throw(_("{0} must be a {1} account.").format(self.purpose, want))
