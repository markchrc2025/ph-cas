import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


def quarter_of(d) -> str:
    d = getdate(d)
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


class PH2307Received(Document):
    def validate(self):
        if getdate(self.period_to) < getdate(self.period_from):
            frappe.throw(_("Period to cannot be before period from."))
        if quarter_of(self.period_from) != quarter_of(self.period_to):
            frappe.throw(_("A 2307 covers one quarter."))
        self.quarter = quarter_of(self.period_from)
        base = tax = 0.0
        for row in self.lines:
            row.base_total = flt(row.month_1) + flt(row.month_2) + flt(row.month_3)
            base += row.base_total
            tax += flt(row.tax_withheld)
        self.total_base = flt(base, 2)
        self.total_tax = flt(tax, 2)
        if self.total_tax <= 0:
            frappe.throw(_("The certificate must show tax withheld."))
        self.warn_if_more_than_deducted()

    def warn_if_more_than_deducted(self):
        """The 2307 should not claim more than the customer actually withheld on payments."""
        deducted = frappe.db.sql(
            """select coalesce(sum(d.amount), 0) from `tabPayment Entry Deduction` d
               join `tabPayment Entry` p on p.name = d.parent
               where p.docstatus = 1 and p.party_type = 'Customer' and p.party = %s and p.company = %s
                 and p.posting_date between %s and %s and d.description like 'Withheld by customer%%'""",
            (self.customer, self.company, self.period_from, self.period_to),
        )[0][0]
        if flt(self.total_tax) > flt(deducted) + 0.01:
            frappe.msgprint(
                _("This 2307 shows {0} withheld but payments in the period booked only {1}. Check the certificate or record the net payment first.").format(
                    frappe.format(self.total_tax, "Currency"), frappe.format(deducted, "Currency")
                ),
                indicator="orange",
            )
