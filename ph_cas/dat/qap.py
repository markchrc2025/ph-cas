"""B28: QAP for the 1601-EQ (layout confirmed against the BIR validator rules
in the reference doc), the annual 1604-E and the MAP for the 1600-VT (both
from the sample layouts, status sample until G5)."""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from ph_cas.dat.writer import agent, file_bytes, file_name, party_fields, record, store

NO_WITHHOLDING_ATC = {"Individual": "DI900", "Non-individual": "EI900"}  # Schedule 2: income not subject to withholding (assumption, RDO 8c)


def _withheld(company, start, end) -> list[dict]:
    rows = frappe.db.sql(
        """select supplier as party, ph_ewt_atc as atc, sum(ph_ewt_base) as income, sum(ph_ewt_amount) as tax
           from `tabPurchase Invoice` where company = %s and docstatus = 1 and posting_date between %s and %s
             and ifnull(ph_ewt_atc, '') != '' and ph_ewt_amount > 0 group by supplier, ph_ewt_atc""",
        (company, start, end), as_dict=True)
    rows += frappe.db.sql(
        """select party, ph_ewt_advance_atc as atc, sum(paid_amount) as income, sum(ph_ewt_on_advance) as tax
           from `tabPayment Entry` where company = %s and party_type = 'Supplier' and docstatus = 1 and posting_date between %s and %s
             and ifnull(ph_ewt_advance_atc, '') != '' and ph_ewt_on_advance > 0 group by party, ph_ewt_advance_atc""",
        (company, start, end), as_dict=True)
    merged = {}
    for r in rows:
        d = merged.setdefault((r.party, r.atc), {"income": 0.0, "tax": 0.0})
        d["income"] += flt(r.income)
        d["tax"] += flt(r.tax)
    out = []
    for (party, atc), d in merged.items():
        p = party_fields("Supplier", party)
        out.append({**p, "atc": atc, "income": d["income"], "tax": d["tax"], "rate": flt(d["tax"] / d["income"] * 100, 2) if d["income"] else 0, "payee_type": frappe.get_cached_value("Supplier", party, "ph_payee_type") or "Non-individual"})
    out.sort(key=lambda x: (x["tin"], x["atc"]))
    return out


def _not_withheld(company, start, end) -> list[dict]:
    rows = frappe.db.sql(
        """select supplier as party, sum(base_net_total) as income from `tabPurchase Invoice`
           where company = %s and docstatus = 1 and posting_date between %s and %s and ph_no_withholding = 1 group by supplier""",
        (company, start, end), as_dict=True)
    out = []
    for r in rows:
        p = party_fields("Supplier", r.party)
        pt = frappe.get_cached_value("Supplier", r.party, "ph_payee_type") or "Non-individual"
        out.append({**p, "atc": NO_WITHHOLDING_ATC[pt], "income": flt(r.income)})
    out.sort(key=lambda x: x["tin"])
    return out


def _names(r):
    if r["registered_name"]:
        return [r["registered_name"], "", "", ""]
    return ["", r["last"], r["first"], r["middle"]]


def build_1601eq(company, start, end):
    a = agent(company)
    lines = [record(["HQAP", "H1601EQ", a["tin"], a["branch"], a["name"], end, a["rdo"]], ["u", "u", "u", "u", "q", "p", "u"])]
    s1 = _withheld(company, start, end)
    ti = tw = 0.0
    for i, r in enumerate(s1, 1):
        lines.append(record(["D1", "1601EQ", i, r["tin"], r["branch"], *_names(r), end, r["atc"], r["rate"], r["income"], r["tax"]], ["u", "u", "i", "u", "u", "qe", "qe", "qe", "qe", "p", "u", "n", "n", "n"]))
        ti += r["income"]
        tw += r["tax"]
    lines.append(record(["C1", "1601EQ", a["tin"], a["branch"], end, ti, tw], ["u", "u", "u", "u", "p", "n", "n"]))
    s2 = _not_withheld(company, start, end)
    t2 = 0.0
    for i, r in enumerate(s2, 1):
        lines.append(record(["D2", "1601EQ", i, r["tin"], r["branch"], *_names(r), end, r["atc"], r["income"]], ["u", "u", "i", "u", "u", "qe", "qe", "qe", "qe", "p", "u", "n"]))
        t2 += r["income"]
    lines.append(record(["C2", "1601EQ", a["tin"], a["branch"], end, t2], ["u", "u", "u", "u", "p", "n"]))
    c = frappe.get_cached_doc("Company", company)
    return file_name(c.tax_id, c.ph_branch_code, end, "1601EQ"), file_bytes(lines), len(s1) + len(s2)


def build_1604e(company, year: int):
    start, end = f"{year}-01-01", f"{year}-12-31"
    a = agent(company)
    lines = [record(["H1604E", a["tin"], a["branch"], end, "N", 0, a["rdo"]], ["u", "u", "u", "d", "u", "i", "u"])]
    s3 = _withheld(company, start, end)
    tw = 0.0
    for i, r in enumerate(s3, 1):
        lines.append(record(["D3", "1604E", a["tin"], a["branch"], end, i, r["tin"], r["branch"], *_names(r), r["atc"], r["income"], r["rate"], r["tax"]], ["u", "u", "u", "u", "d", "i", "u", "u", "qe", "qe", "qe", "qe", "u", "n", "n", "n"]))
        tw += r["tax"]
    lines.append(record(["C3", "1604E", a["tin"], a["branch"], end, tw], ["u", "u", "u", "u", "d", "n"]))
    s4 = _not_withheld(company, start, end)
    ti = 0.0
    for i, r in enumerate(s4, 1):
        lines.append(record(["D4", "1604E", a["tin"], a["branch"], end, i, r["tin"], r["branch"], *_names(r), r["atc"], r["income"]], ["u", "u", "u", "u", "d", "i", "u", "u", "qe", "qe", "qe", "qe", "u", "n"]))
        ti += r["income"]
    lines.append(record(["C4", "1604E", a["tin"], a["branch"], end, ti], ["u", "u", "u", "u", "d", "n"]))
    c = frappe.get_cached_doc("Company", company)
    return file_name(c.tax_id, c.ph_branch_code, end, "1604E", kind="annual"), file_bytes(lines), len(s3) + len(s4)


def build_1600vt(company, start, end):
    a = agent(company)
    rows = frappe.db.sql(
        """select supplier as party, ph_rc_atc as atc, sum(ph_rc_base) as income, sum(ph_rc_vat) as tax from `tabPurchase Invoice`
           where company = %s and docstatus = 1 and posting_date between %s and %s and ifnull(ph_rc_atc, '') != '' group by supplier, ph_rc_atc""",
        (company, start, end), as_dict=True)
    data = []
    for r in rows:
        s = frappe.get_cached_doc("Supplier", r.party)
        if s.get("ph_tin") or s.get("tax_id"):
            p = party_fields("Supplier", r.party)
        else:  # a non-resident provider has no Philippine TIN
            p = {"tin": "000000000", "branch": "0000", "registered_name": (s.get("ph_registered_name") or s.supplier_name or r.party).upper(), "last": "", "first": "", "middle": ""}
        data.append({**p, "atc": r.atc, "income": flt(r.income), "tax": flt(r.tax), "rate": flt(r.tax / r.income * 100, 2) if r.income else 0})
    data.sort(key=lambda x: (x["tin"], x["atc"]))
    lines = [record(["HMAP", "H1600VT", a["tin"], a["branch"], a["name"], end, a["rdo"]], ["u", "u", "u", "u", "q", "p", "u"])]
    ti = tw = 0.0
    for i, r in enumerate(data, 1):
        lines.append(record(["DMAP", "D1600VT", i, r["tin"], r["branch"], r["registered_name"], r["last"], r["first"], r["middle"], end, r["atc"], "", r["rate"], r["income"], r["tax"]], ["u", "u", "i", "u", "u", "u", "u", "u", "u", "p", "u", "e", "n", "n", "n"]))
        ti += r["income"]
        tw += r["tax"]
    lines.append(record(["CMAP", "C1600VT", a["tin"], a["branch"], end, ti, tw], ["u", "u", "u", "u", "p", "n", "n"]))
    c = frappe.get_cached_doc("Company", company)
    return file_name(c.tax_id, c.ph_branch_code, end, "1600VT"), file_bytes(lines), len(data)


STATUS = {"1601EQ": "verified-layout (validator rules; golden file pending)", "1604E": "sample", "1600VT": "sample"}


@frappe.whitelist()
def generate(company: str, form: str, period_start: str, period_end: str) -> str:
    frappe.has_permission("PH Alphalist File", "create", throw=True)
    if form == "1601EQ":
        name, content, n = build_1601eq(company, period_start, period_end)
    elif form == "1604E":
        name, content, n = build_1604e(company, getdate(period_end).year)
    elif form == "1600VT":
        name, content, n = build_1600vt(company, period_start, period_end)
    else:
        frappe.throw(_("Unknown form {0}.").format(form))
    frappe.flags.ph_dat_writer = True
    try:
        return store(company, form, period_start, period_end, name, content, STATUS[form], n)
    finally:
        frappe.flags.ph_dat_writer = False


def unknown_atcs() -> list[str]:
    """ATCs the engine uses that the Alphalist module 7.4 does not list (RDO question 8c)."""
    known_missing = {"WI840", "WC840", "WI850", "WC850", "WI860", "WC860", "WV080", "WV090", "WV100", "WV110"}
    used = {r[0] for r in frappe.db.sql("select distinct ph_ewt_atc from `tabPurchase Invoice` where ifnull(ph_ewt_atc,'') != ''")}
    used |= {r[0] for r in frappe.db.sql("select distinct ph_rc_atc from `tabPurchase Invoice` where ifnull(ph_rc_atc,'') != ''")}
    return sorted(used & known_missing)
