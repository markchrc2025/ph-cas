"""B09: the Philippine fields on Company, Customer, Supplier, Item and the
invoice lines, plus the RDO table."""

import json
import os
import re

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

VAT_STATUS = "VAT\nNon-VAT\nVAT-exempt"
TAXPAYER_CLASS = "Micro\nSmall\nMedium\nLarge"  # RR 8-2024
VAT_CLASS = "VATable\nVAT-exempt\nZero-rated\nGovernment"
PAYEE_TYPE = "Individual\nNon-individual"
TIN_RE = re.compile(r"^\d{3}-?\d{3}-?\d{3}$")


def company_fields():
    return [
        {"fieldname": "ph_section", "fieldtype": "Section Break", "label": "BIR registration (Philippines)", "insert_after": "tax_id"},
        {"fieldname": "ph_registered_name", "fieldtype": "Data", "label": "Registered name (per COR)", "insert_after": "ph_section"},
        {"fieldname": "ph_business_style", "fieldtype": "Data", "label": "Business style / trade name", "insert_after": "ph_registered_name"},
        {"fieldname": "ph_branch_code", "fieldtype": "Data", "label": "Branch code (5 digits)", "default": "00000", "length": 5, "insert_after": "ph_business_style"},
        {"fieldname": "ph_rdo", "fieldtype": "Link", "label": "RDO", "options": "PH RDO", "insert_after": "ph_branch_code"},
        {"fieldname": "ph_col1", "fieldtype": "Column Break", "insert_after": "ph_rdo"},
        {"fieldname": "ph_vat_status", "fieldtype": "Select", "label": "VAT status", "options": VAT_STATUS, "default": "Non-VAT", "insert_after": "ph_col1"},
        {"fieldname": "ph_taxpayer_class", "fieldtype": "Select", "label": "Taxpayer classification (RR 8-2024)", "options": TAXPAYER_CLASS, "default": "Micro", "insert_after": "ph_vat_status"},
        {"fieldname": "ph_taxpayer_type", "fieldtype": "Select", "label": "Taxpayer type", "options": "Individual\nNon-individual", "default": "Non-individual", "insert_after": "ph_taxpayer_class"},
        {"fieldname": "ph_top_withholding_agent", "fieldtype": "Check", "label": "Top withholding agent (RR 24-2025)", "insert_after": "ph_taxpayer_type"},
        {"fieldname": "ph_cas_section", "fieldtype": "Section Break", "label": "CAS registration", "insert_after": "ph_top_withholding_agent"},
        {"fieldname": "ph_accn", "fieldtype": "Data", "label": "ACCN", "insert_after": "ph_cas_section"},
        {"fieldname": "ph_accn_date", "fieldtype": "Date", "label": "Date issued", "insert_after": "ph_accn"},
        # F0: what a BIR return prints about the taxpayer (ph_cas.forms.needs asks for what is blank)
        {"fieldname": "ph_taxpayer_section", "fieldtype": "Section Break", "label": "Taxpayer details (BIR returns)", "insert_after": "ph_accn_date", "collapsible": 1},
        {"fieldname": "ph_last_name", "fieldtype": "Data", "label": "Last name", "insert_after": "ph_taxpayer_section", "depends_on": "eval:doc.ph_taxpayer_type=='Individual'"},
        {"fieldname": "ph_first_name", "fieldtype": "Data", "label": "First name", "insert_after": "ph_last_name", "depends_on": "eval:doc.ph_taxpayer_type=='Individual'"},
        {"fieldname": "ph_middle_name", "fieldtype": "Data", "label": "Middle name", "insert_after": "ph_first_name", "depends_on": "eval:doc.ph_taxpayer_type=='Individual'"},
        {"fieldname": "ph_birthdate", "fieldtype": "Date", "label": "Date of birth", "insert_after": "ph_middle_name", "depends_on": "eval:doc.ph_taxpayer_type=='Individual'"},
        {"fieldname": "ph_civil_status", "fieldtype": "Select", "label": "Civil status", "options": "\nSingle\nMarried\nLegally Separated\nWidow/er", "insert_after": "ph_birthdate", "depends_on": "eval:doc.ph_taxpayer_type=='Individual'"},
        {"fieldname": "ph_citizenship", "fieldtype": "Data", "label": "Citizenship", "default": "Filipino", "insert_after": "ph_civil_status", "depends_on": "eval:doc.ph_taxpayer_type=='Individual'"},
        {"fieldname": "ph_incorporation_date", "fieldtype": "Date", "label": "Date of incorporation or organization", "insert_after": "ph_citizenship", "depends_on": "eval:doc.ph_taxpayer_type!='Individual'"},
        {"fieldname": "ph_taxpayer_col", "fieldtype": "Column Break", "insert_after": "ph_incorporation_date"},
        {"fieldname": "ph_registered_address", "fieldtype": "Small Text", "label": "Registered address (per COR)", "insert_after": "ph_taxpayer_col"},
        {"fieldname": "ph_zip", "fieldtype": "Data", "label": "ZIP code", "length": 4, "insert_after": "ph_registered_address"},
        {"fieldname": "ph_contact_number", "fieldtype": "Data", "label": "Contact number", "insert_after": "ph_zip"},
        {"fieldname": "ph_email", "fieldtype": "Data", "label": "Email address (as registered)", "options": "Email", "insert_after": "ph_contact_number"},
        {"fieldname": "ph_line_of_business", "fieldtype": "Data", "label": "Line of business", "insert_after": "ph_email"},
        {"fieldname": "ph_psic", "fieldtype": "Data", "label": "PSIC code", "length": 5, "insert_after": "ph_line_of_business"},
        {"fieldname": "ph_fiscal_year_start", "fieldtype": "Date", "label": "Fiscal year start (blank = calendar year)", "insert_after": "ph_psic", "description": "The first day of the fiscal year, for the 2550Q, 1702Q and 1702-RT. Withholding returns and the 2551Q follow the calendar."},
    ]


def party_fields(prefix_after: str):
    return [
        {"fieldname": "ph_section", "fieldtype": "Section Break", "label": "BIR details (Philippines)", "insert_after": prefix_after},
        {"fieldname": "ph_tin", "fieldtype": "Data", "label": "TIN (9 digits)", "length": 11, "insert_after": "ph_section"},
        {"fieldname": "ph_branch_code", "fieldtype": "Data", "label": "Branch code (5 digits)", "default": "00000", "length": 5, "insert_after": "ph_tin"},
        {"fieldname": "ph_registered_name", "fieldtype": "Data", "label": "Registered name (non-individual)", "insert_after": "ph_branch_code"},
        {"fieldname": "ph_payee_type", "fieldtype": "Select", "label": "Payee type", "options": PAYEE_TYPE, "default": "Non-individual", "insert_after": "ph_registered_name"},
        {"fieldname": "ph_last_name", "fieldtype": "Data", "label": "Last name", "insert_after": "ph_payee_type", "depends_on": "eval:doc.ph_payee_type=='Individual'"},
        {"fieldname": "ph_first_name", "fieldtype": "Data", "label": "First name", "insert_after": "ph_last_name", "depends_on": "eval:doc.ph_payee_type=='Individual'"},
        {"fieldname": "ph_middle_name", "fieldtype": "Data", "label": "Middle name", "insert_after": "ph_first_name", "depends_on": "eval:doc.ph_payee_type=='Individual'"},
        {"fieldname": "ph_col1", "fieldtype": "Column Break", "insert_after": "ph_middle_name"},
        {"fieldname": "ph_vat_status", "fieldtype": "Select", "label": "VAT status", "options": VAT_STATUS, "default": "Non-VAT", "insert_after": "ph_col1"},
        {"fieldname": "ph_is_government", "fieldtype": "Check", "label": "Government agency or GOCC", "insert_after": "ph_vat_status"},
        {"fieldname": "ph_top_withholding_agent", "fieldtype": "Check", "label": "Top withholding agent", "insert_after": "ph_is_government"},
        {"fieldname": "ph_is_rbe", "fieldtype": "Check", "label": "Registered business enterprise (RR 9-2025)", "insert_after": "ph_top_withholding_agent"},
        {"fieldname": "ph_is_nonresident_dsp", "fieldtype": "Check", "label": "Non-resident digital service provider (RA 12023)", "insert_after": "ph_is_rbe"},
        {"fieldname": "ph_is_platform", "fieldtype": "Check", "label": "Online platform / marketplace (RR 5-2025)", "insert_after": "ph_is_nonresident_dsp"},
        {"fieldname": "ph_address_line1", "fieldtype": "Data", "label": "Registered address line 1", "insert_after": "ph_is_platform"},
        {"fieldname": "ph_address_line2", "fieldtype": "Data", "label": "Registered address line 2", "insert_after": "ph_address_line1"},
        {"fieldname": "ph_zip", "fieldtype": "Data", "label": "ZIP code", "length": 4, "insert_after": "ph_address_line2"},
    ]


def item_fields():
    return [
        {"fieldname": "ph_vat_class", "fieldtype": "Select", "label": "VAT class", "options": VAT_CLASS, "default": "VATable", "insert_after": "item_group"},
        {"fieldname": "ph_is_capital_good", "fieldtype": "Check", "label": "Capital good (depreciable)", "insert_after": "ph_vat_class"},
    ]


def line_fields(after: str):
    return [
        # The leading empty option matters: Frappe fills a Select with its first
        # option on new rows, which would defeat the fetch from the item.
        {"fieldname": "ph_vat_class", "fieldtype": "Select", "label": "VAT class", "options": "\n" + VAT_CLASS, "fetch_from": "item_code.ph_vat_class", "fetch_if_empty": 1, "insert_after": after, "in_list_view": 0, "default": ""},
    ]


def setup():
    fields = {
        "Company": company_fields(),
        "Customer": party_fields("tax_id"),
        "Supplier": party_fields("tax_id"),
        "Item": item_fields(),
        "Sales Invoice Item": line_fields("item_name"),
        "Purchase Invoice Item": line_fields("item_name"),
        "POS Invoice Item": line_fields("item_name"),
    }
    fields = {k: v for k, v in fields.items() if frappe.db.exists("DocType", k)}
    create_custom_fields(fields, ignore_validate=True, update=True)
    seed_rdos()


def seed_rdos():
    path = os.path.join(os.path.dirname(__file__), "data", "rdo.json")
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    for r in rows:
        if not frappe.db.exists("PH RDO", r["rdo_code"]):
            frappe.get_doc(r).insert(ignore_permissions=True)


# ---- validation ---------------------------------------------------------


def normalize_tin(tin: str) -> str:
    digits = re.sub(r"\D", "", tin or "")
    return f"{digits[0:3]}-{digits[3:6]}-{digits[6:9]}" if len(digits) == 9 else tin


def validate_tin(tin: str, label: str = "TIN"):
    if not tin:
        return
    digits = re.sub(r"\D", "", tin)
    if len(digits) == 12:
        frappe.throw(_("{0}: enter the 9-digit TIN and the 5-digit branch code separately (the TIN {1} carries a branch code).").format(label, tin))
    if not TIN_RE.match(tin) and len(digits) != 9:
        frappe.throw(_("{0} must be 9 digits (000-000-000).").format(label))


def validate_branch(code: str, label: str = "Branch code"):
    code = (code or "").strip()
    if code and not (code.isdigit() and len(code) == 5):
        frappe.throw(_("{0} must be exactly 5 digits (00000 for the head office).").format(label))


def dat_branch(code: str) -> str:
    """The 4-digit branch code the alphalist DAT files take (RDO question 8b):
    a 5-digit code with a leading zero drops it; anything else is refused."""
    code = (code or "00000").strip() or "00000"
    validate_branch(code)
    if code[0] != "0":
        frappe.throw(_("Branch code {0} cannot be written in a 4-digit DAT field. Ask the RDO (question 8b).").format(code))
    return code[1:]


def validate_company(doc, method=None):
    if doc.get("tax_id"):
        validate_tin(doc.tax_id, _("Company TIN"))
        doc.tax_id = normalize_tin(doc.tax_id)
    validate_branch(doc.get("ph_branch_code"))
    if not doc.get("ph_branch_code"):
        doc.ph_branch_code = "00000"
    if not doc.get("ph_registered_name"):
        doc.ph_registered_name = doc.company_name


def validate_party(doc, method=None):
    if doc.get("ph_tin"):
        validate_tin(doc.ph_tin)
        doc.ph_tin = normalize_tin(doc.ph_tin)
        if not doc.get("tax_id"):
            doc.tax_id = doc.ph_tin
    elif doc.get("tax_id") and TIN_RE.match(doc.tax_id.strip()):
        doc.ph_tin = normalize_tin(doc.tax_id)
    validate_branch(doc.get("ph_branch_code"))
    if not doc.get("ph_branch_code"):
        doc.ph_branch_code = "00000"
    if doc.get("ph_payee_type") == "Individual":
        if not (doc.get("ph_last_name") and doc.get("ph_first_name")):
            frappe.throw(_("An individual payee needs a last name and a first name (the alphalist reports them separately)."))
    else:
        if not doc.get("ph_registered_name"):
            doc.ph_registered_name = doc.get("customer_name") or doc.get("supplier_name")
    if doc.get("ph_is_nonresident_dsp") and doc.doctype != "Supplier":
        frappe.throw(_("Only a Supplier can be a non-resident digital service provider."))


def payee_name_parts(party_doctype: str, party: str) -> dict:
    """Name fields as the alphalist wants them."""
    d = frappe.get_cached_doc(party_doctype, party)
    if d.get("ph_payee_type") == "Individual":
        return {"registered_name": "", "last": d.get("ph_last_name") or "", "first": d.get("ph_first_name") or "", "middle": d.get("ph_middle_name") or ""}
    return {"registered_name": d.get("ph_registered_name") or d.get("customer_name") or d.get("supplier_name") or d.name, "last": "", "first": "", "middle": ""}
