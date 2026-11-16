"""B14: the purchase side. Input VAT by kind, expanded withholding by supplier
profile, timing, and the no-withholding flag.

- A VAT company booking a bill from a VAT supplier gets input VAT rows by
  kind (goods, services, capital goods) to the mapped accounts. A Non-VAT
  company treats the VAT as cost (one row to Taxes and Licenses).
- Expanded withholding is a Deduct tax row to the EWT payable account, from
  the supplier's withholding category and payee type and the rule in force
  on the bill date (RR 4-2024: withhold at accrual, recording or the supplier's
  invoice, whichever first). The amounts are tagged for the 2307 (B26), the
  QAP and the alphalists (B27, B28).
- A bill may be booked without withholding only with a written reason
  (RMC 60-2024: the expense stays deductible; the duty and penalties remain).
- An advance payment to a supplier with a withholding category withholds at
  payment (the earlier event).
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from ph_cas.setup.chart import account_for
from ph_cas.tax.rules import PHNoRuleError, resolve

INPUT_VAT_PREFIX = "Input VAT"
EWT_PREFIX = "EWT"
VAT_COST_DESCRIPTION = "VAT on purchases (cost, Non-VAT buyer)"

CATEGORIES = "\nNone (no withholding)\nprofessional\nrent\ncontractor\ngoods\nservices\nreduced_wholesale"

SUPPLIER_FIELDS = [
    {"fieldname": "ph_ewt_section", "fieldtype": "Section Break", "label": "Expanded withholding", "insert_after": "ph_zip"},
    {"fieldname": "ph_ewt_category", "fieldtype": "Select", "label": "Withholding category", "options": CATEGORIES, "insert_after": "ph_ewt_section", "description": "What this supplier is paid for. goods and services apply only when the company is a top withholding agent."},
    {"fieldname": "ph_over_threshold", "fieldtype": "Check", "label": "Gross income over the threshold, or VAT-registered (professionals: the higher rate)", "insert_after": "ph_ewt_category"},
]

PI_FIELDS = [
    {"fieldname": "ph_tax_section", "fieldtype": "Section Break", "label": "Philippine tax", "insert_after": "taxes_and_charges", "collapsible": 1},
    {"fieldname": "ph_input_vat_goods", "fieldtype": "Currency", "label": "Input VAT: goods", "read_only": 1, "insert_after": "ph_tax_section"},
    {"fieldname": "ph_input_vat_services", "fieldtype": "Currency", "label": "Input VAT: services", "read_only": 1, "insert_after": "ph_input_vat_goods"},
    {"fieldname": "ph_input_vat_capital", "fieldtype": "Currency", "label": "Input VAT: capital goods", "read_only": 1, "insert_after": "ph_input_vat_services"},
    {"fieldname": "ph_vat_cost", "fieldtype": "Currency", "label": "VAT treated as cost", "read_only": 1, "insert_after": "ph_input_vat_capital"},
    {"fieldname": "ph_exempt_purchases", "fieldtype": "Currency", "label": "Purchases without VAT (exempt or Non-VAT supplier)", "read_only": 1, "insert_after": "ph_vat_cost"},
    {"fieldname": "ph_tax_col", "fieldtype": "Column Break", "insert_after": "ph_exempt_purchases"},
    {"fieldname": "ph_ewt_atc", "fieldtype": "Data", "label": "EWT ATC", "read_only": 1, "insert_after": "ph_tax_col"},
    {"fieldname": "ph_ewt_rate", "fieldtype": "Percent", "label": "EWT rate (%)", "read_only": 1, "insert_after": "ph_ewt_atc"},
    {"fieldname": "ph_ewt_base", "fieldtype": "Currency", "label": "EWT base (net of VAT)", "read_only": 1, "insert_after": "ph_ewt_rate"},
    {"fieldname": "ph_ewt_amount", "fieldtype": "Currency", "label": "EWT withheld", "read_only": 1, "insert_after": "ph_ewt_base", "bold": 1},
    {"fieldname": "ph_ewt_rule", "fieldtype": "Data", "label": "Rules applied", "read_only": 1, "insert_after": "ph_ewt_amount"},
    {"fieldname": "ph_no_withholding", "fieldtype": "Check", "label": "Book without withholding", "insert_after": "ph_ewt_rule"},
    {"fieldname": "ph_no_withholding_reason", "fieldtype": "Small Text", "label": "Reason for not withholding", "insert_after": "ph_no_withholding", "depends_on": "ph_no_withholding", "mandatory_depends_on": "ph_no_withholding"},
    {"fieldname": "ph_ewt_period", "fieldtype": "Data", "label": "Withholding period (YYYY-MM)", "read_only": 1, "insert_after": "ph_no_withholding_reason"},
]

PE_FIELDS = [
    {"fieldname": "ph_ewt_on_advance", "fieldtype": "Currency", "label": "EWT withheld on this advance", "read_only": 1, "insert_after": "ph_wht_deducted"},
    {"fieldname": "ph_ewt_advance_atc", "fieldtype": "Data", "label": "EWT ATC (advance)", "read_only": 1, "insert_after": "ph_ewt_on_advance"},
]


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Supplier": SUPPLIER_FIELDS, "Purchase Invoice": PI_FIELDS, "Payment Entry": PE_FIELDS}, ignore_validate=True, update=True)


def _company(doc):
    return frappe.get_cached_doc("Company", doc.company)


def _line_base(row) -> float:
    if row.get("net_amount") is not None and flt(row.get("net_amount")):
        return flt(row.net_amount)
    if row.get("amount") is not None and flt(row.get("amount")):
        return flt(row.amount)
    return flt(row.get("qty")) * flt(row.get("rate"))


def _kind(row) -> str:
    if not row.get("item_code"):
        return "services"
    item = frappe.get_cached_doc("Item", row.item_code)
    if item.get("ph_is_capital_good") or item.get("is_fixed_asset"):
        return "capital"
    return "goods" if item.is_stock_item else "services"


def _line_vat_class(row) -> str:
    cls = row.get("ph_vat_class")
    if not cls and row.get("item_code"):
        cls = frappe.get_cached_value("Item", row.item_code, "ph_vat_class")
    return cls or "VATable"


def ewt_profile(supplier_doc, company_doc) -> dict | None:
    """Selectors for the EWT rule, or None when nothing applies."""
    category = (supplier_doc.get("ph_ewt_category") or "").strip()
    if category.startswith("None") or not category:
        return None
    if category in ("goods", "services"):
        if not company_doc.get("ph_top_withholding_agent"):
            return None
        category = f"twa_{category}"
    sel = {"category": category, "payee_type": supplier_doc.get("ph_payee_type") or "Non-individual"}
    if category == "professional":
        sel["over_threshold"] = "1" if supplier_doc.get("ph_over_threshold") else "0"
    return sel


def before_validate(doc, method=None):
    """doc_events['Purchase Invoice'].before_validate"""
    company = _company(doc)
    supplier = frappe.get_cached_doc("Supplier", doc.supplier)
    date = getdate(doc.posting_date)
    keep = [t for t in (doc.get("taxes") or []) if not ((t.get("description") or "").startswith(INPUT_VAT_PREFIX) or (t.get("description") or "").startswith(EWT_PREFIX) or t.get("description") == VAT_COST_DESCRIPTION)]
    doc.taxes = keep
    cost_center = doc.get("cost_center") or company.cost_center

    # ---- input VAT
    bases = {"goods": 0.0, "services": 0.0, "capital": 0.0}
    exempt = 0.0
    supplier_vat = (supplier.get("ph_vat_status") or "Non-VAT") == "VAT" and not supplier.get("ph_is_nonresident_dsp") and not supplier.get("ph_is_rbe") and not doc.get("ph_is_import")
    for row in doc.get("items") or []:
        base = _line_base(row)
        cls = _line_vat_class(row)
        row.ph_vat_class = cls
        if supplier_vat and cls in ("VATable", "Government"):
            bases[_kind(row)] += base
        else:
            exempt += base
    doc.ph_exempt_purchases = flt(exempt, 2)
    from ph_cas.tax.line_scope import scope_purchase

    scope_purchase(doc, supplier_vat, _line_vat_class, _kind)  # input VAT only on its own lines (LDG-112)
    doc.ph_input_vat_goods = doc.ph_input_vat_services = doc.ph_input_vat_capital = doc.ph_vat_cost = 0
    rules = []
    if supplier_vat and any(bases.values()):
        rule = resolve("vat", date, side="purchase")
        rules.append(rule.rule_id)
        if (company.get("ph_vat_status") or "Non-VAT") == "VAT":
            for kind, base in bases.items():
                if not base:
                    continue
                r = rule
                if kind == "capital":
                    r = resolve("vat", date, side="purchase", capital_good="1")
                    rules.append(r.rule_id)
                amount = flt(base * flt(r.rate) / 100, 2)
                purpose = {"goods": "input_vat_goods", "services": "input_vat_services", "capital": "input_vat_capital"}[kind]
                doc.append("taxes", {"charge_type": "Actual", "add_deduct_tax": "Add", "category": "Total", "account_head": account_for(doc.company, purpose), "description": f"{INPUT_VAT_PREFIX} ({kind})", "tax_amount": amount, "cost_center": cost_center})
                doc.set(f"ph_input_vat_{kind}", amount)
        else:
            total_base = sum(bases.values())
            amount = flt(total_base * flt(rule.rate) / 100, 2)
            doc.append("taxes", {"charge_type": "Actual", "add_deduct_tax": "Add", "category": "Total", "account_head": account_for(doc.company, "percentage_tax_expense"), "description": VAT_COST_DESCRIPTION, "tax_amount": amount, "cost_center": cost_center})
            doc.ph_vat_cost = amount

    if doc.get("ph_is_import") and flt(doc.get("ph_input_vat_import")) and (company.get("ph_vat_status") or "Non-VAT") == "VAT":
        # VAT paid to the Bureau of Customs is input VAT on importation; booked against the import VAT account
        doc.append("taxes", {"charge_type": "Actual", "add_deduct_tax": "Add", "category": "Total", "account_head": account_for(doc.company, "input_vat_import"), "description": f"{INPUT_VAT_PREFIX} (importation)", "tax_amount": flt(doc.ph_input_vat_import, 2), "cost_center": cost_center})

    # ---- expanded withholding
    doc.ph_ewt_atc = None
    doc.ph_ewt_rate = doc.ph_ewt_base = doc.ph_ewt_amount = 0
    doc.ph_ewt_period = f"{date.year}-{date.month:02d}"
    sel = ewt_profile(supplier, company)
    if sel and not doc.get("ph_no_withholding"):
        r = resolve("ewt", date, **sel)
        base = flt(sum(bases.values()) + exempt, 2)  # the income payment, net of VAT
        amount = flt(base * flt(r.rate) / 100, 2)
        if amount:
            doc.append("taxes", {"charge_type": "Actual", "add_deduct_tax": "Deduct", "category": "Total", "account_head": account_for(doc.company, "ewt_payable"), "description": f"{EWT_PREFIX} {r.atc} {flt(r.rate):g}%", "tax_amount": amount, "cost_center": cost_center})
        doc.ph_ewt_atc, doc.ph_ewt_rate, doc.ph_ewt_base, doc.ph_ewt_amount = r.atc, flt(r.rate), base, amount
        rules.append(r.rule_id)
    doc.ph_ewt_rule = ",".join(rules)


def validate(doc, method=None):
    if doc.get("ph_no_withholding") and not (doc.get("ph_no_withholding_reason") or "").strip():
        frappe.throw(_("Give the reason for booking this bill without withholding (RMC 60-2024: the duty to withhold remains)."))
    supplier = frappe.get_cached_doc("Supplier", doc.supplier)
    if doc.get("ph_no_withholding") and not ewt_profile(supplier, _company(doc)):
        frappe.msgprint(_("This supplier has no withholding category; the flag has no effect."), indicator="orange")


def payment_before_validate(doc, method=None):
    """Advance to a supplier (no references): withhold at payment, the earlier event."""
    doc.ph_ewt_on_advance = 0
    doc.ph_ewt_advance_atc = None
    if doc.get("payment_type") != "Pay" or doc.get("party_type") != "Supplier":
        return
    doc.deductions = [d for d in (doc.get("deductions") or []) if not (d.get("description") or "").startswith("EWT on advance")]
    if doc.get("references"):
        return
    supplier = frappe.get_cached_doc("Supplier", doc.party)
    sel = ewt_profile(supplier, _company(doc))
    if not sel:
        return
    try:
        r = resolve("ewt", doc.posting_date, **sel)
    except PHNoRuleError:
        return
    paid = flt(doc.paid_amount)
    base = flt(paid / 1.12, 2) if (supplier.get("ph_vat_status") or "") == "VAT" else paid
    amount = flt(base * flt(r.rate) / 100, 2)
    if amount <= 0:
        return
    # The supplier receives paid_amount; the withheld part is a deduction credited to EWT payable:
    # a negative deduction increases the amount applied to the party against the cash paid.
    doc.append("deductions", {"account": account_for(doc.company, "ewt_payable"), "cost_center": _company(doc).cost_center, "amount": -amount, "description": f"EWT on advance {r.atc} {flt(r.rate):g}%"})
    doc.ph_ewt_on_advance = amount
    doc.ph_ewt_advance_atc = r.atc
