import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from ph_cas.tax.returns import quarter_bounds


class PH2307Issued(Document):
    def autoname(self):
        qs, qe = quarter_bounds(self.period_from)
        self.quarter = f"{qs.year}-Q{(qs.month - 1) // 3 + 1}"
        base = f"2307-{self.quarter}-{self.supplier}"
        self.name = base
        n = 1
        while frappe.db.exists("PH 2307 Issued", self.name):
            n += 1
            self.name = f"{base}-{n}"  # a reissue after a cancelled certificate

    def validate(self):
        qs, qe = quarter_bounds(self.period_from)
        if getdate(self.period_to) > qe or getdate(self.period_from) < qs:
            frappe.throw(_("A 2307 covers one quarter."))
        self.quarter = f"{qs.year}-Q{(qs.month - 1) // 3 + 1}"
        if self.is_new() or not self.lines:
            self.generate()
        self.fill_payee()
        inc = tax = 0.0
        for r in self.lines:
            r.total = flt(r.month_1) + flt(r.month_2) + flt(r.month_3)
            inc += r.total
            tax += flt(r.tax_withheld)
        self.total_income = flt(inc, 2)
        self.total_tax = flt(tax, 2)
        if not self.lines:
            frappe.throw(_("Nothing was withheld from {0} in {1}.").format(self.supplier, self.quarter))
        if self.is_new():
            dup = frappe.db.exists("PH 2307 Issued", {"company": self.company, "supplier": self.supplier, "quarter": self.quarter, "docstatus": 1})
            if dup:
                frappe.throw(_("A certificate for {0} for {1} was already issued ({2}). Cancel it first to reissue.").format(self.supplier, self.quarter, dup))

    def before_submit(self):
        self.issued_on = nowdate()

    def fill_payee(self):
        s = frappe.get_cached_doc("Supplier", self.supplier)
        tin = s.get("ph_tin") or s.get("tax_id") or ""
        self.payee_tin = f"{tin}-{s.get('ph_branch_code') or '00000'}" if tin else ""
        if s.get("ph_payee_type") == "Individual":
            self.payee_name = ", ".join(p for p in [s.get("ph_last_name"), s.get("ph_first_name"), s.get("ph_middle_name")] if p)
        else:
            self.payee_name = s.get("ph_registered_name") or s.supplier_name
        self.payee_address = ", ".join(p for p in [s.get("ph_address_line1"), s.get("ph_address_line2")] if p)
        self.payee_zip = s.get("ph_zip") or ""

    def generate(self):
        """Lines from the bills and advances of the quarter, per ATC, by month."""
        qs, qe = quarter_bounds(self.period_from)
        rows = frappe.db.sql(
            """select ph_ewt_atc as atc, month(posting_date) as m, sum(ph_ewt_base) as base, sum(ph_ewt_amount) as tax
               from `tabPurchase Invoice` where company = %s and supplier = %s and docstatus = 1
                 and posting_date between %s and %s and ifnull(ph_ewt_atc, '') != '' and ph_ewt_amount > 0
               group by ph_ewt_atc, month(posting_date)""",
            (self.company, self.supplier, qs, qe),
            as_dict=True,
        )
        rows += frappe.db.sql(
            """select ph_ewt_advance_atc as atc, month(posting_date) as m, sum(paid_amount) as base, sum(ph_ewt_on_advance) as tax
               from `tabPayment Entry` where company = %s and party_type = 'Supplier' and party = %s and docstatus = 1
                 and posting_date between %s and %s and ifnull(ph_ewt_advance_atc, '') != '' and ph_ewt_on_advance > 0
               group by ph_ewt_advance_atc, month(posting_date)""",
            (self.company, self.supplier, qs, qe),
            as_dict=True,
        )
        by_atc = {}
        for r in rows:
            d = by_atc.setdefault(r.atc, {"month_1": 0.0, "month_2": 0.0, "month_3": 0.0, "tax_withheld": 0.0})
            idx = (int(r.m) - qs.month) + 1
            d[f"month_{idx}"] += flt(r.base)
            d["tax_withheld"] += flt(r.tax)
        self.set("lines", [])
        for atc in sorted(by_atc):
            d = by_atc[atc]
            title = frappe.db.get_value("PH Tax Rule", {"atc": atc, "kind": "ewt"}, "title") or atc
            self.append("lines", {"description": title[:140], "atc": atc, "block": "A", **{k: flt(v, 2) for k, v in d.items()}})


@frappe.whitelist()
def generate_quarter(company: str, quarter_start: str) -> list:
    """One certificate per payee withheld from in the quarter. Returns the names."""
    frappe.has_permission("PH 2307 Issued", "create", throw=True)
    qs, qe = quarter_bounds(quarter_start)
    suppliers = {r[0] for r in frappe.db.sql("select distinct supplier from `tabPurchase Invoice` where company = %s and docstatus = 1 and posting_date between %s and %s and ph_ewt_amount > 0", (company, qs, qe))}
    suppliers |= {r[0] for r in frappe.db.sql("select distinct party from `tabPayment Entry` where company = %s and party_type = 'Supplier' and docstatus = 1 and posting_date between %s and %s and ph_ewt_on_advance > 0", (company, qs, qe))}
    out = []
    quarter = f"{qs.year}-Q{(qs.month - 1) // 3 + 1}"
    for s in sorted(suppliers):
        if frappe.db.exists("PH 2307 Issued", {"company": company, "supplier": s, "quarter": quarter, "docstatus": ("<", 2)}):
            continue
        doc = frappe.get_doc({"doctype": "PH 2307 Issued", "company": company, "supplier": s, "period_from": qs, "period_to": qe}).insert()
        out.append(doc.name)
    return out
