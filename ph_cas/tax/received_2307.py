"""B94 (owner, 27 Nov 2026): the customer's 2307, from the sales invoice it covers.

A sales invoice the customer withheld tax on gets "BIR 2307" > Upload the customer's 2307: the
scan is saved as a PH 2307 Received linked to the invoice (lines by ATC and month, the file as
its attachment). The income tax returns (1701Q, 1702Q, 1701, 1702-RT) claim those certificates
(income_tax._credits_2307, the SAWT), list them as their attachments, and warn, without
blocking, about invoices whose 2307 has not come in."""

import io
import zipfile

import frappe
from frappe import _
from frappe.utils import flt, get_last_day, getdate


ITR_FORMS = ("1701Q", "1702Q", "1701", "1702-RT")


def _quarter_bounds(d):
    d = getdate(d)
    m0 = (d.month - 1) // 3 * 3 + 1
    start = d.replace(month=m0, day=1)
    return start, get_last_day(start.replace(month=m0 + 2))


@frappe.whitelist()
def for_invoice(invoice: str) -> dict:
    si = frappe.get_doc("Sales Invoice", invoice)
    si.check_permission("read")
    withheld = flt(si.get("ph_wht_amount"))
    names = frappe.get_all("PH 2307 Received Invoice", filters={"sales_invoice": invoice, "parenttype": "PH 2307 Received"}, pluck="parent")
    received = []
    for n in sorted(set(names)):
        r = frappe.db.get_value("PH 2307 Received", n, ["name", "docstatus", "attachment"], as_dict=True)
        if r and r.docstatus < 2:
            received.append({"name": r.name, "file": r.attachment})
    return {"withheld": withheld, "atc": si.get("ph_wht_atc"), "base": flt(si.get("ph_wht_base")), "received": received}


@frappe.whitelist()
def record_for_invoice(invoice: str, file: str, atc: str, income, tax, received_on=None) -> str:
    si = frappe.get_doc("Sales Invoice", invoice)
    si.check_permission("read")
    frappe.has_permission("PH 2307 Received", "create", throw=True)
    if si.docstatus != 1:
        frappe.throw(_("Upload the 2307 for a submitted invoice."))
    if flt(tax) <= 0:
        frappe.throw(_("The 2307 must show tax withheld."))
    start, end = _quarter_bounds(si.posting_date)
    idx = getdate(si.posting_date).month - start.month + 1
    doc = frappe.get_doc(
        {
            "doctype": "PH 2307 Received",
            "company": si.company,
            "customer": si.customer,
            "period_from": start,
            "period_to": end,
            "certificate_date": received_on or getdate(),
            "attachment": file,
            "remarks": _("Uploaded from {0}").format(invoice),
            "lines": [{"atc": (atc or "").strip().upper(), "kind": "Income tax", f"month_{idx}": flt(income, 2), "tax_withheld": flt(tax, 2)}],
            "invoices": [{"sales_invoice": invoice, "tax_withheld": flt(tax, 2)}],
        }
    )
    doc.insert()
    doc.submit()
    f = frappe.db.get_value("File", {"file_url": file}, "name")
    if f:
        frappe.db.set_value("File", f, {"attached_to_doctype": "PH 2307 Received", "attached_to_name": doc.name})
    return doc.name


def missing(company: str, start, end) -> list[dict]:
    """Submitted sales invoices in the period on which the customer withheld income tax and that no
    2307 Received covers."""
    return frappe.db.sql(
        """select si.name, si.customer, si.posting_date, si.ph_wht_amount as withheld
           from `tabSales Invoice` si
           where si.company = %s and si.docstatus = 1 and si.is_return = 0 and si.posting_date between %s and %s
             and ifnull(si.ph_wht_amount, 0) > 0
             and not exists (select 1 from `tabPH 2307 Received Invoice` ri join `tabPH 2307 Received` r on r.name = ri.parent
                             where ri.sales_invoice = si.name and r.docstatus = 1)
           order by si.posting_date, si.name""",
        (company, start, end),
        as_dict=True,
    )


def received(company: str, start, end) -> list[dict]:
    return frappe.get_all(
        "PH 2307 Received",
        filters={"company": company, "docstatus": 1, "period_from": (">=", start), "period_to": ("<=", end)},
        fields=["name", "customer", "quarter", "total_tax", "attachment"],
        order_by="period_from, name",
    )


def warnings_for(form: str, company: str, start, end) -> list[str]:
    if form not in ITR_FORMS:
        return []
    out = []
    gone = missing(company, start, end)
    if gone:
        total = sum(flt(r.withheld) for r in gone)
        out.append(
            _("{0} sales invoice(s) with {1} withheld by customers have no 2307 yet (not claimed until received): {2}").format(
                len(gone), frappe.format(total, {"fieldtype": "Currency"}), ", ".join(r.name for r in gone[:10]) + ("..." if len(gone) > 10 else "")
            )
        )
    noscan = [r.name for r in received(company, start, end) if not r.attachment]
    if noscan:
        out.append(_("These 2307s have no scan attached: {0}").format(", ".join(noscan[:10])))
    return out


def attachments_zip(company: str, start, end) -> tuple[str, bytes]:
    rows = received(company, start, end)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        index = ["2307,Customer,Quarter,Tax withheld,File"]
        for r in rows:
            fname = ""
            if r.attachment:
                f = frappe.get_doc("File", {"file_url": r.attachment})
                fname = f"{r.name}_{f.file_name}"
                z.writestr(fname, f.get_content())
            index.append(f'{r.name},"{r.customer}",{r.quarter},{flt(r.total_tax, 2):.2f},{fname}')
        z.writestr("00_INDEX.csv", "\r\n".join(index) + "\r\n")
    return f"2307s_received_{company.replace(' ', '_')}_{start}_{end}.zip", buf.getvalue()
