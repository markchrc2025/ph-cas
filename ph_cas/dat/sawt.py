"""B27: SAWT (Summary Alphalist of Withholding Taxes), attached by the payee
to the return that claims the credit: 2550Q (VAT withheld), 2551Q
(percentage tax withheld), 1701Q, 1702Q, 1701, 1702 (income tax withheld).
Source: PH 2307 Received. Layout from the sample doc (status: sample until G5):
  H: HSAWT,H<FORM>,TIN,BC,"Reg name","Last","First","Middle",MM/YYYY,RDO
  D: DSAWT,D<FORM>,seq,TIN,BC,"Reg name" or empty,"Last","First","Middle" or empty,MM/YYYY,(empty),ATC,rate,income,withheld
  C: CSAWT,C<FORM>,TIN,BC,MM/YYYY,total income,total withheld
Rows sorted by TIN. Unused name side left as unquoted empty fields.
"""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.dat.writer import agent, file_bytes, file_name, party_fields, record, store

KIND_BY_FORM = {"2550Q": "VAT", "2551Q": "Percentage tax", "1701Q": "Income tax", "1702Q": "Income tax", "1701": "Income tax", "1702": "Income tax", "1702RT": "Income tax"}
LAYOUT_STATUS = "sample"


def rows_for(company: str, form: str, start, end) -> list[dict]:
    kind = KIND_BY_FORM[form]
    data = frappe.db.sql(
        """select d.customer, l.atc, sum(l.base_total) as income, sum(l.tax_withheld) as tax
           from `tabPH 2307 Received Line` l join `tabPH 2307 Received` d on d.name = l.parent
           where d.docstatus = 1 and d.company = %s and l.kind = %s and d.period_from >= %s and d.period_to <= %s
           group by d.customer, l.atc""",
        (company, kind, start, end),
        as_dict=True,
    )
    out = []
    for r in data:
        p = party_fields("Customer", r.customer)
        rate = flt(flt(r.tax) / flt(r.income) * 100, 2) if flt(r.income) else 0
        out.append({**p, "atc": r.atc, "rate": rate, "income": flt(r.income), "tax": flt(r.tax)})
    out.sort(key=lambda x: (x["tin"], x["atc"]))
    return out


def build(company: str, form: str, start, end) -> tuple[str, bytes, int]:
    if form not in KIND_BY_FORM:
        frappe.throw(_("No SAWT for {0}.").format(form))
    a = agent(company)
    rows = rows_for(company, form, start, end)
    fcode = form.replace("-", "")
    lines = [record(["HSAWT", f"H{fcode}", a["tin"], a["branch"], a["name"] if not a["individual"] else "", a["last"], a["first"], a["middle"], end, a["rdo"]], ["u", "u", "u", "u", "q", "q", "q", "q", "p", "u"])]
    ti = tw = 0.0
    for i, r in enumerate(rows, 1):
        if r["registered_name"]:
            names = [r["registered_name"], "", "", ""]
            kinds = ["q", "e", "e", "e"]
        else:
            names = ["", r["last"], r["first"], r["middle"]]
            kinds = ["e", "q", "q", "q"]
        lines.append(record(["DSAWT", f"D{fcode}", i, r["tin"], r["branch"], *names, end, "", r["atc"], r["rate"], r["income"], r["tax"]], ["u", "u", "i", "u", "u", *kinds, "p", "e", "u", "n", "n", "n"]))
        ti += r["income"]
        tw += r["tax"]
    lines.append(record(["CSAWT", f"C{fcode}", a["tin"], a["branch"], end, ti, tw], ["u", "u", "u", "u", "p", "n", "n"]))
    name = file_name(frappe.get_cached_value("Company", company, "tax_id"), frappe.get_cached_value("Company", company, "ph_branch_code"), end, fcode)
    return name, file_bytes(lines), len(rows)


@frappe.whitelist()
def generate(company: str, form: str, period_start: str, period_end: str) -> str:
    frappe.has_permission("PH Alphalist File", "create", throw=True)
    name, content, n = build(company, form, period_start, period_end)
    frappe.flags.ph_dat_writer = True
    try:
        return store(company, f"SAWT-{form}", period_start, period_end, name, content, LAYOUT_STATUS, n)
    finally:
        frappe.flags.ph_dat_writer = False
