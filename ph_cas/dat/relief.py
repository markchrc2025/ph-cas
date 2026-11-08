"""B29: the summary lists of sales, purchases and importations (RELIEF /
SLSP), filed with the 2550Q by every VAT taxpayer. Layouts from the sample
doc (status: sample; the BIR's own format, gate G7, overrides it):

  Sales file TIN9+S+MMYYYY.DAT
    H,S,"TIN","Reg name","Last","First","Middle","Trade name","Addr1","Addr2",exempt,zero,taxable,output VAT,RDO,MM/DD/YYYY,fiscal month
    D,S,"Customer TIN","Reg name","Last","First","Middle",addr1,addr2,exempt,zero,taxable,output VAT,own TIN,MM/DD/YYYY
  Purchases file TIN9+P+MMYYYY.DAT
    H,P,... ,exempt,zero,services,capital goods,goods other than capital,input VAT,creditable input VAT,non-creditable input VAT,RDO,MM/DD/YYYY,fiscal month
    D,P,"Supplier TIN","Reg name","Last","First","Middle",addr1,addr2,exempt,zero,services,capital,goods,input VAT,own TIN,MM/DD/YYYY
  Importations file TIN9+I+MMYYYY.DAT
    D,I,import entry no,assessment date,"Supplier",importation date,country,dutiable value,charges,exempt,taxable,VAT,OR no,payment date,own TIN,MM/DD/YYYY
Rows are merged per TIN.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt, getdate

from ph_cas.dat.writer import CRLF, agent, file_bytes, record, store, tin9

IMPORT_FIELDS = [
    {"fieldname": "ph_import_section", "fieldtype": "Section Break", "label": "Importation (for the summary list and 2550Q item 46)", "insert_after": "ph_supplier_claimed_ovc", "collapsible": 1},
    {"fieldname": "ph_is_import", "fieldtype": "Check", "label": "This bill is an importation", "insert_after": "ph_import_section"},
    {"fieldname": "ph_import_entry_no", "fieldtype": "Data", "label": "Import entry number", "insert_after": "ph_is_import", "depends_on": "ph_is_import"},
    {"fieldname": "ph_import_assessment_date", "fieldtype": "Date", "label": "Assessment date", "insert_after": "ph_import_entry_no", "depends_on": "ph_is_import"},
    {"fieldname": "ph_import_date", "fieldtype": "Date", "label": "Date of importation", "insert_after": "ph_import_assessment_date", "depends_on": "ph_is_import"},
    {"fieldname": "ph_import_country", "fieldtype": "Data", "label": "Country of origin", "insert_after": "ph_import_date", "depends_on": "ph_is_import"},
    {"fieldname": "ph_import_col", "fieldtype": "Column Break", "insert_after": "ph_import_country"},
    {"fieldname": "ph_import_dutiable_value", "fieldtype": "Currency", "label": "Dutiable value", "insert_after": "ph_import_col", "depends_on": "ph_is_import"},
    {"fieldname": "ph_import_charges", "fieldtype": "Currency", "label": "Customs duties and charges", "insert_after": "ph_import_dutiable_value", "depends_on": "ph_is_import"},
    {"fieldname": "ph_input_vat_import", "fieldtype": "Currency", "label": "VAT paid to the Bureau of Customs", "insert_after": "ph_import_charges", "depends_on": "ph_is_import"},
    {"fieldname": "ph_import_or_no", "fieldtype": "Data", "label": "OR number", "insert_after": "ph_input_vat_import", "depends_on": "ph_is_import"},
    {"fieldname": "ph_import_payment_date", "fieldtype": "Date", "label": "Date of VAT payment", "insert_after": "ph_import_or_no", "depends_on": "ph_is_import"},
]

STATUS = "sample"


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Purchase Invoice": IMPORT_FIELDS}, ignore_validate=True, update=True)


def _party(doctype, name):
    d = frappe.get_cached_doc(doctype, name)
    tin = re.sub(r"\D", "", d.get("ph_tin") or d.get("tax_id") or "") or "000000000"
    if d.get("ph_payee_type") == "Individual":
        names = ["", (d.get("ph_last_name") or "").upper(), (d.get("ph_first_name") or "").upper(), (d.get("ph_middle_name") or "").upper()]
    else:
        names = [(d.get("ph_registered_name") or d.get("customer_name") or d.get("supplier_name") or name).upper(), "", "", ""]
    return tin, names, (d.get("ph_address_line1") or "").upper(), (d.get("ph_address_line2") or "").upper()


def _agent_header(company, end):
    c = frappe.get_cached_doc("Company", company)
    a = agent(company)
    return a, (c.get("ph_business_style") or "").upper(), c


def _fname(company, letter, end):
    c = frappe.get_cached_doc("Company", company)
    d = getdate(end)
    return f"{tin9(c.tax_id)}{letter}{d.month:02d}{d.year}.DAT"


def build_sales(company, start, end):
    a, trade, c = _agent_header(company, end)
    rows = frappe.db.sql(
        """select customer, sum(ph_exempt_sales) as exempt, sum(ph_zero_rated_sales) as zero, sum(ph_vatable_sales) as taxable, sum(ph_vat_amount) as vat
           from `tabSales Invoice` where company = %s and docstatus = 1 and posting_date between %s and %s group by customer""",
        (company, start, end), as_dict=True)
    merged = {}
    for r in rows:
        tin, names, a1, a2 = _party("Customer", r.customer)
        m = merged.setdefault(tin, {"names": names, "a1": a1, "a2": a2, "exempt": 0.0, "zero": 0.0, "taxable": 0.0, "vat": 0.0})
        for k in ("exempt", "zero", "taxable", "vat"):
            m[k] += flt(r[k])
    tot = {k: sum(m[k] for m in merged.values()) for k in ("exempt", "zero", "taxable", "vat")}
    lines = [record(["H", "S", a["tin"], a["name"], "", "", "", trade, "", "", tot["exempt"], tot["zero"], tot["taxable"], tot["vat"], a["rdo"], end, 12], ["u", "u", "q", "q", "q", "q", "q", "q", "q", "q", "n", "n", "n", "n", "u", "d", "i"])]
    for tin in sorted(merged):
        m = merged[tin]
        lines.append(record(["D", "S", tin, *m["names"], m["a1"], m["a2"], m["exempt"], m["zero"], m["taxable"], m["vat"], a["tin"], end], ["u", "u", "q", "q", "q", "q", "q", "u", "u", "n", "n", "n", "n", "u", "d"]))
    return _fname(company, "S", end), file_bytes(lines), len(merged)


def build_purchases(company, start, end):
    a, trade, c = _agent_header(company, end)
    from ph_cas.tax.rules import resolve

    rate = flt(resolve("vat", end, side="purchase").rate) or 12
    rows = frappe.db.sql(
        """select supplier, sum(ph_exempt_purchases) as exempt, sum(ph_input_vat_services) as vs, sum(ph_input_vat_capital) as vc, sum(ph_input_vat_goods) as vg
           from `tabPurchase Invoice` where company = %s and docstatus = 1 and posting_date between %s and %s and ifnull(ph_is_import, 0) = 0 group by supplier""",
        (company, start, end), as_dict=True)
    merged = {}
    for r in rows:
        tin, names, a1, a2 = _party("Supplier", r.supplier)
        m = merged.setdefault(tin, {"names": names, "a1": a1, "a2": a2, "exempt": 0.0, "zero": 0.0, "services": 0.0, "capital": 0.0, "goods": 0.0, "vat": 0.0})
        m["exempt"] += flt(r.exempt)
        m["services"] += flt(r.vs) * 100 / rate
        m["capital"] += flt(r.vc) * 100 / rate
        m["goods"] += flt(r.vg) * 100 / rate
        m["vat"] += flt(r.vs) + flt(r.vc) + flt(r.vg)
    keys = ("exempt", "zero", "services", "capital", "goods", "vat")
    tot = {k: flt(sum(m[k] for m in merged.values()), 2) for k in keys}
    # non-creditable input VAT: the ratable share attributable to exempt sales (2550Q item 53), from the quarter's figures when computed
    noncred = 0.0
    fig = frappe.db.get_value("PH Tax Return Figures", {"company": company, "form": "2550Q", "period_start": start, "period_end": end}, "name")
    if fig:
        noncred = frappe.get_doc("PH Tax Return Figures", fig).figure("53B")
    lines = [record(["H", "P", a["tin"], a["name"], "", "", "", trade, "", "", tot["exempt"], tot["zero"], tot["services"], tot["capital"], tot["goods"], tot["vat"], flt(tot["vat"] - noncred, 2), noncred, a["rdo"], end, 12], ["u", "u", "q", "q", "q", "q", "q", "q", "q", "q", "n", "n", "n", "n", "n", "n", "n", "n", "u", "d", "i"])]
    for tin in sorted(merged):
        m = merged[tin]
        lines.append(record(["D", "P", tin, *m["names"], m["a1"], m["a2"], m["exempt"], m["zero"], m["services"], m["capital"], m["goods"], m["vat"], a["tin"], end], ["u", "u", "q", "q", "q", "q", "q", "u", "u", "n", "n", "n", "n", "n", "n", "u", "d"]))
    return _fname(company, "P", end), file_bytes(lines), len(merged)


def build_importations(company, start, end):
    a, trade, c = _agent_header(company, end)
    bills = frappe.get_all("Purchase Invoice", filters={"company": company, "docstatus": 1, "ph_is_import": 1, "posting_date": ("between", [start, end])},
                           fields=["supplier_name", "ph_import_entry_no", "ph_import_assessment_date", "ph_import_date", "ph_import_country", "ph_import_dutiable_value", "ph_import_charges", "ph_exempt_purchases", "ph_input_vat_import", "ph_import_or_no", "ph_import_payment_date"], order_by="posting_date")
    lines = []
    for b in bills:
        taxable = flt(b.ph_import_dutiable_value) + flt(b.ph_import_charges) - flt(b.ph_exempt_purchases)
        lines.append(record(["D", "I", b.ph_import_entry_no or "", b.ph_import_assessment_date or end, (b.supplier_name or "").upper(), b.ph_import_date or end, (b.ph_import_country or "").upper(), b.ph_import_dutiable_value, b.ph_import_charges, b.ph_exempt_purchases, taxable, b.ph_input_vat_import, b.ph_import_or_no or "", b.ph_import_payment_date or end, a["tin"], end], ["u", "u", "u", "d", "q", "d", "u", "n", "n", "n", "n", "n", "u", "d", "u", "d"]))
    return _fname(company, "I", end), file_bytes(lines) if lines else b"", len(lines)


@frappe.whitelist()
def generate(company: str, kind: str, period_start: str, period_end: str) -> str:
    frappe.has_permission("PH Alphalist File", "create", throw=True)
    builder = {"S": build_sales, "P": build_purchases, "I": build_importations}[kind]
    name, content, n = builder(company, period_start, period_end)
    frappe.flags.ph_dat_writer = True
    try:
        return store(company, f"RELIEF-{kind}", period_start, period_end, name, content, STATUS, n)
    finally:
        frappe.flags.ph_dat_writer = False
