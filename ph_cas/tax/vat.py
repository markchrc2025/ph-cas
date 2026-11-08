"""B12: the sales side. VAT classes, output VAT and the percentage-tax base.

Prices are VAT-exclusive (the invoice lists net amounts; VAT is added as a
tax row). A VAT company gets one Actual tax row "Output VAT" computed from the
VATable and Government lines at the rule rate in force on the posting date.
A Non-VAT company gets no VAT row; the percentage-tax base is recorded on the
invoice for the 2551Q (B17). Every invoice stores its buckets.
"""

import frappe
from frappe import _
from frappe.utils import flt

from ph_cas.setup.chart import account_for
from ph_cas.tax.rules import resolve

OUTPUT_VAT_DESCRIPTION = "Output VAT"
CLASSES = ("VATable", "VAT-exempt", "Zero-rated", "Government")

BUCKET_FIELDS = [
    {"fieldname": "ph_tax_section", "fieldtype": "Section Break", "label": "Philippine tax", "insert_after": "taxes_and_charges", "collapsible": 1},
    {"fieldname": "ph_tax_regime", "fieldtype": "Select", "label": "Seller's tax regime", "options": "\nVAT\nNon-VAT\nVAT-exempt", "read_only": 1, "insert_after": "ph_tax_section"},
    {"fieldname": "ph_vatable_sales", "fieldtype": "Currency", "label": "VATable sales", "read_only": 1, "insert_after": "ph_tax_regime"},
    {"fieldname": "ph_vat_amount", "fieldtype": "Currency", "label": "VAT amount", "read_only": 1, "insert_after": "ph_vatable_sales"},
    {"fieldname": "ph_government_sales", "fieldtype": "Currency", "label": "Sales to government (VATable)", "read_only": 1, "insert_after": "ph_vat_amount"},
    {"fieldname": "ph_tax_col", "fieldtype": "Column Break", "insert_after": "ph_government_sales"},
    {"fieldname": "ph_zero_rated_sales", "fieldtype": "Currency", "label": "Zero-rated sales", "read_only": 1, "insert_after": "ph_tax_col"},
    {"fieldname": "ph_exempt_sales", "fieldtype": "Currency", "label": "VAT-exempt sales", "read_only": 1, "insert_after": "ph_zero_rated_sales"},
    {"fieldname": "ph_pt_base", "fieldtype": "Currency", "label": "Sales subject to percentage tax", "read_only": 1, "insert_after": "ph_exempt_sales"},
    {"fieldname": "ph_vat_rate", "fieldtype": "Percent", "label": "VAT rate applied", "read_only": 1, "insert_after": "ph_pt_base"},
    {"fieldname": "ph_vat_rule", "fieldtype": "Data", "label": "VAT rule", "read_only": 1, "insert_after": "ph_vat_rate"},
]


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Sales Invoice": BUCKET_FIELDS, "POS Invoice": BUCKET_FIELDS}, ignore_validate=True, update=True)


def company_regime(company: str) -> str:
    status = frappe.get_cached_value("Company", company, "ph_vat_status") or "Non-VAT"
    return status


def line_class(row) -> str:
    cls = row.get("ph_vat_class")
    if not cls and row.get("item_code"):
        cls = frappe.get_cached_value("Item", row.item_code, "ph_vat_class")
    return cls or "VATable"


def _line_base(row) -> float:
    """Net amount of a line; before ERPNext has computed totals (before_validate)
    fall back to qty times rate less the line discount."""
    if row.get("net_amount") is not None and flt(row.get("net_amount")):
        return flt(row.net_amount)
    if row.get("amount") is not None and flt(row.get("amount")):
        return flt(row.amount)
    base = flt(row.get("qty")) * flt(row.get("rate") or row.get("price_list_rate"))
    return base


def buckets(doc) -> dict:
    b = {c: 0.0 for c in CLASSES}
    for row in doc.get("items") or []:
        cls = line_class(row)
        row.ph_vat_class = cls
        b[cls] = b.get(cls, 0.0) + _line_base(row)
    return b


def before_validate(doc, method=None):
    """doc_events['Sales Invoice'/'POS Invoice'].before_validate: set the
    output VAT row before ERPNext computes totals."""
    regime = company_regime(doc.company)
    doc.ph_tax_regime = regime
    b = buckets(doc)
    # drop any earlier Output VAT row; it is recomputed below
    doc.taxes = [t for t in (doc.get("taxes") or []) if (t.get("description") or "") != OUTPUT_VAT_DESCRIPTION]
    if regime == "VAT":
        rule = resolve("vat", doc.posting_date, **{"class": "VATable"})
        vat_base = b["VATable"] + b["Government"]
        vat = flt(vat_base * flt(rule.rate) / 100, 2)
        doc.ph_vat_rate = flt(rule.rate)
        doc.ph_vat_rule = rule.rule_id
        if vat_base:
            doc.append(
                "taxes",
                {
                    "charge_type": "Actual",
                    "account_head": account_for(doc.company, "output_vat"),
                    "description": OUTPUT_VAT_DESCRIPTION,
                    "tax_amount": vat,
                    "cost_center": doc.get("cost_center") or frappe.get_cached_value("Company", doc.company, "cost_center"),
                },
            )
    else:
        doc.ph_vat_rate = 0
        doc.ph_vat_rule = None


def validate(doc, method=None):
    """doc_events['Sales Invoice'/'POS Invoice'].validate: record the buckets
    after ERPNext's totals are final, and check the classes."""
    regime = doc.ph_tax_regime or company_regime(doc.company)
    b = buckets(doc)
    if regime != "VAT" and (b["Zero-rated"] or b["Government"]):
        frappe.throw(_("A Non-VAT seller cannot issue zero-rated or VAT-on-government lines. Use VATable (percentage tax) or VAT-exempt."))
    doc.ph_vatable_sales = flt(b["VATable"] + b["Government"], 2) if regime == "VAT" else 0
    doc.ph_government_sales = flt(b["Government"], 2) if regime == "VAT" else 0
    doc.ph_zero_rated_sales = flt(b["Zero-rated"], 2)
    doc.ph_exempt_sales = flt(b["VAT-exempt"], 2)
    vat_rows = [t for t in (doc.get("taxes") or []) if (t.get("description") or "") == OUTPUT_VAT_DESCRIPTION]
    doc.ph_vat_amount = flt(sum(flt(t.tax_amount) for t in vat_rows), 2)
    doc.ph_pt_base = flt(b["VATable"] + b["Government"], 2) if regime == "Non-VAT" else 0


def gross_sales_last_12_months(company: str, as_of=None) -> float:
    from frappe.utils import add_months, getdate, nowdate

    as_of = getdate(as_of or nowdate())
    start = add_months(as_of, -12)
    row = frappe.db.sql(
        """select coalesce(sum(base_net_total), 0) from `tabSales Invoice`
           where company = %s and docstatus = 1 and posting_date > %s and posting_date <= %s""",
        (company, start, as_of),
    )
    return flt(row[0][0]) if row else 0.0


def threshold_status(company: str, as_of=None) -> dict:
    from frappe.utils import nowdate

    rule = resolve("threshold", as_of or nowdate(), base="gross_sales_12m")
    gross = gross_sales_last_12_months(company, as_of)
    return {"gross_12m": gross, "threshold": flt(rule.threshold), "exceeded": gross > flt(rule.threshold), "rule": rule.rule_id}
