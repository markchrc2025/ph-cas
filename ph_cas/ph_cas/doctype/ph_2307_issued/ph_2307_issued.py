import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, nowdate

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
        if self.docstatus == 0:
            self.status = "Draft"
            self.generate()  # a draft always shows the quarter's bills as they stand (QA pass 4)
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
        """B90: a submitted certificate is locked; it is Printed once printed and Issued once handed over."""
        self.status = "Draft"
        if self.amended_from and not self.replaces:
            self.replaces = self.amended_from

    def on_cancel(self):
        self.db_set("status", "Cancelled", update_modified=False)

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
        """Lines from the bills and advances of the quarter, per ATC, by month.

        B90: every bill and payment that withheld tax is listed under Sources, so the
        certificate shows where each peso of tax came from."""
        qs, qe = quarter_bounds(self.period_from)
        docs = frappe.db.sql(
            """select 'Purchase Invoice' as dt, name, posting_date, bill_no as ref, ph_ewt_atc as atc, ph_ewt_base as base, ph_ewt_amount as tax
               from `tabPurchase Invoice` where company = %s and supplier = %s and docstatus = 1
                 and posting_date between %s and %s and ifnull(ph_ewt_atc, '') != '' and ph_ewt_amount > 0
               order by posting_date, name""",
            (self.company, self.supplier, qs, qe),
            as_dict=True,
        )
        docs += frappe.db.sql(
            """select 'Payment Entry' as dt, name, posting_date, reference_no as ref, ph_ewt_advance_atc as atc, paid_amount as base, ph_ewt_on_advance as tax
               from `tabPayment Entry` where company = %s and party_type = 'Supplier' and party = %s and docstatus = 1
                 and posting_date between %s and %s and ifnull(ph_ewt_advance_atc, '') != '' and ph_ewt_on_advance > 0
               order by posting_date, name""",
            (self.company, self.supplier, qs, qe),
            as_dict=True,
        )
        by_atc = {}
        self.set("sources", [])
        for r in docs:
            idx = (getdate(r.posting_date).month - qs.month) + 1
            d = by_atc.setdefault(r.atc, {"month_1": 0.0, "month_2": 0.0, "month_3": 0.0, "tax_withheld": 0.0})
            d[f"month_{idx}"] += flt(r.base)
            d["tax_withheld"] += flt(r.tax)
            self.append("sources", {"source_doctype": r.dt, "source_name": r.name, "posting_date": r.posting_date, "reference": r.ref, "atc": r.atc, "month": idx, "base": flt(r.base, 2), "tax_withheld": flt(r.tax, 2)})
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
        if frappe.db.exists("PH 2307 Issued", {"company": company, "supplier": s, "quarter": quarter, "docstatus": 1}):
            continue  # issued: a change goes through cancel and reissue
        draft = frappe.db.get_value("PH 2307 Issued", {"company": company, "supplier": s, "quarter": quarter, "docstatus": 0}, "name")
        if draft:
            doc = frappe.get_doc("PH 2307 Issued", draft)
            doc.save()  # brought up to date with the bills posted since it was made
            out.append(doc.name)
            continue
        doc = frappe.get_doc({"doctype": "PH 2307 Issued", "company": company, "supplier": s, "period_from": qs, "period_to": qe}).insert()
        out.append(doc.name)
    return out


@frappe.whitelist()
def print_bir_form(name: str):
    """Print the certificate on page 1 of the BIR 2307 blank and attach it.

    B90 (owner, 25 Nov 2026): a 2307 is issued to the supplier, not filed, so it
    prints clean (no watermark, no preview line). Printing locks it: a draft is
    submitted first, so the figures on paper never change. The first print sets
    the status to Printed; Mark as issued sets Issued. A correction is a cancel
    and amend."""
    from ph_cas.audit.events import record
    from ph_cas.forms import f2307
    from ph_cas.forms.engine import taxpayer_block
    from ph_cas.forms.export import ExportRefusal

    cert = frappe.get_doc("PH 2307 Issued", name)
    cert.check_permission("read")
    if cert.docstatus == 2:
        frappe.throw(_("{0} is cancelled. Amend it to print a corrected certificate.").format(name))
    if cert.docstatus == 0:
        cert.check_permission("submit")
        cert.save()  # brought up to date with the bills posted since it was made
        cert.submit()
    c = taxpayer_block(frappe.get_cached_doc("Company", cert.company))
    qn = (cert.period_from.month - 1) // 3 + 1
    try:
        pdf = f2307.certificate_pdf(cert, c, {}, qn, cert.period_from.year, None, None)
    except ExportRefusal as e:
        frappe.throw(str(e))
    fname = f"{name} BIR 2307.pdf"
    for old in frappe.get_all("File", {"attached_to_doctype": "PH 2307 Issued", "attached_to_name": name, "file_name": ["like", f"{name} BIR 2307%"]}, pluck="name"):
        frappe.delete_doc("File", old, ignore_permissions=True, force=True)
    f = frappe.get_doc({"doctype": "File", "file_name": fname, "attached_to_doctype": "PH 2307 Issued", "attached_to_name": name, "is_private": 1, "content": pdf})
    f.flags.ignore_permissions = True
    f.insert()
    n = int(cert.print_count or 0) + 1
    cert.db_set("print_count", n, update_modified=False)
    if not cert.printed_on:
        cert.db_set("printed_on", now_datetime(), update_modified=False)
    if cert.status in (None, "", "Draft"):
        cert.db_set("status", "Printed", update_modified=False)
    record("print", "PH 2307 Issued", name, 1, {"print_no": n, "copy": "original" if n == 1 else "reprint"})
    return f.file_url


@frappe.whitelist()
def mark_issued(name: str, issued_on: str | None = None):
    """B90: the certificate was handed to the supplier on issued_on (today by default)."""
    from ph_cas.audit.events import record

    cert = frappe.get_doc("PH 2307 Issued", name)
    cert.check_permission("submit")
    if cert.docstatus != 1 or cert.status not in ("Printed", "Issued"):
        frappe.throw(_("Print the certificate before marking it issued."))
    day = getdate(issued_on or nowdate())
    if day > getdate(nowdate()):
        frappe.throw(_("The issue date cannot be in the future."))
    if cert.printed_on and day < getdate(cert.printed_on):
        frappe.throw(_("The issue date cannot be before the first print ({0}).").format(frappe.format(getdate(cert.printed_on), {"fieldtype": "Date"})))
    cert.db_set("issued_on", day, update_modified=False)
    cert.db_set("status", "Issued", update_modified=False)
    record("2307_issued", "PH 2307 Issued", name, 1, {"issued_on": str(day)})
    return {"status": "Issued", "issued_on": str(day)}
