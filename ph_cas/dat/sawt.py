"""B27, B62: SAWT (Summary Alphalist of Withholding Taxes), attached by the payee
to the return that claims the credit: 2550Q (VAT withheld), 2551Q (percentage tax
withheld), 1701Q, 1702Q, 1701, 1702 (income tax withheld). Source: PH 2307 Received.

Verified on 16 Nov 2026 against the BIR Alphalist Data Entry and Validation module
7.4: its Data Entry module wrote the golden file in ph_cas/tests/golden/alphalist/
from dummy data, its Validation module passes it, and this writer reproduces it byte
for byte (test_b62_alphalist_golden).
  H: HSAWT,H<FORM>,TIN,BC4,"Reg name","Last","First","Middle",MM/YYYY,RDO
  D: DSAWT,D<FORM>,seq,TIN,BC4,"Reg name" or empty,"Last","First","Middle" or empty,MM/YYYY,(empty),ATC,rate,income,withheld
  C: CSAWT,C<FORM>,TIN,BC4,MM/YYYY,total income,total withheld
The header quotes every name field ("" when blank); a detail row quotes a name only
when it has a value. Rows sorted by TIN, then ATC. The module lists the SAWT forms
1700, 1701, 1701Q, 1702, 1702Q, 2550M, 2550Q, 2551Q and 2553: the 1702-RT, 1702-EX
and 1702-MX all file under 1702. The quarter's rows carry the quarter's last month,
the way the module records a quarterly return.
"""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.dat.writer import agent, file_bytes, file_name, party_fields, record, store

KIND_BY_FORM = {"2550Q": "VAT", "2551Q": "Percentage tax", "1701Q": "Income tax", "1702Q": "Income tax", "1701": "Income tax", "1702": "Income tax"}
LAYOUT_STATUS = "verified"


def _code(form: str) -> str:
    """The form as the SAWT writes it: the dash dropped (BIR Returns writes 1702-RT), and
    the 1702-RT, 1702-EX and 1702-MX all under 1702, the only annual corporate SAWT the
    module lists."""
    code = (form or "").replace("-", "").upper()
    return "1702" if code in ("1702RT", "1702EX", "1702MX") else code


def rows_for(company: str, form: str, start, end) -> list[dict]:
    kind = KIND_BY_FORM[_code(form)]
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


def sawt_file(a: dict, fcode: str, period_end, rows: list[dict]) -> bytes:
    lines = [record(["HSAWT", f"H{fcode}", a["tin"], a["branch"], a["name"] if not a["individual"] else "", a["last"], a["first"], a["middle"], period_end, a["rdo"]], ["u", "u", "u", "u", "q", "q", "q", "q", "p", "u"])]
    ti = tw = 0.0
    for i, r in enumerate(rows, 1):
        names = [r["registered_name"], "", "", ""] if r["registered_name"] else ["", r["last"], r["first"], r["middle"]]
        lines.append(record(["DSAWT", f"D{fcode}", i, r["tin"], r["branch"], *names, period_end, "", r["atc"], r["rate"], r["income"], r["tax"]], ["u", "u", "i", "u", "u", "qn", "qn", "qn", "qn", "p", "e", "u", "n", "n", "n"]))
        ti += r["income"]
        tw += r["tax"]
    lines.append(record(["CSAWT", f"C{fcode}", a["tin"], a["branch"], period_end, ti, tw], ["u", "u", "u", "u", "p", "n", "n"]))
    return file_bytes(lines)


def build(company: str, form: str, start, end) -> tuple[str, bytes, int]:
    if _code(form) not in KIND_BY_FORM:
        frappe.throw(_("No SAWT for {0}.").format(form))
    rows = rows_for(company, form, start, end)
    fcode = _code(form)
    name = file_name(frappe.get_cached_value("Company", company, "tax_id"), frappe.get_cached_value("Company", company, "ph_branch_code"), end, fcode)
    return name, sawt_file(agent(company), fcode, end, rows), len(rows)


@frappe.whitelist()
def generate(company: str, form: str, period_start: str, period_end: str) -> str:
    frappe.has_permission("PH Alphalist File", "create", throw=True)
    name, content, n = build(company, form, period_start, period_end)
    if not n:
        # the validator rejects a SAWT with no detail ("No Detail Record found in file!")
        frappe.throw(_("No 2307 received for the {0} in this period, so there is no SAWT to write.").format(form), title=_("No SAWT"))
    frappe.flags.ph_dat_writer = True
    try:
        return store(company, f"SAWT-{_code(form)}", period_start, period_end, name, content, LAYOUT_STATUS, n)
    finally:
        frappe.flags.ph_dat_writer = False
