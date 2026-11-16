"""LDG-112: each VAT row sits only on the lines it belongs to.

The engine books VAT as Actual tax rows (vat.py, purchase.py). ERPNext v16
splits an Actual row over the lines whose item tax map does not mark the
row's account "N/A", and it rebuilds every line's map from the line's Item Tax
Template on each save. Without a template the output VAT of an invoice was
also shown on its VAT-exempt and zero-rated lines in the per-line tax breakup
(Item Wise Tax Detail and the form's breakup table); totals and the ledger
were right.

So each company gets a few Item Tax Templates of its own, marking the VAT
accounts a line does not carry as not applicable, and the engine puts one on
each line by its VAT class (and, on bills, its kind):

- "PH No VAT": VAT-exempt and zero-rated lines, and bills from non-VAT
  suppliers: no output VAT, input VAT or VAT-as-cost.
- "PH Input VAT goods" / "services" / "capital": a VATable bill line carries
  only the input VAT row of its own kind.

A line whose template was chosen by a person (not one of these) is left alone.
"""

import frappe
from frappe.utils import flt

NO_VAT = "PH No VAT"
KINDS = ("goods", "services", "capital")
VAT_PURPOSES = ("output_vat", "input_vat_goods", "input_vat_services", "input_vat_capital", "input_vat_import", "percentage_tax_expense")


def _accounts(company: str) -> dict:
    rows = frappe.get_all("PH Account Mapping", filters={"company": company, "purpose": ("in", VAT_PURPOSES)}, fields=["purpose", "account"])
    # an Item Tax Template takes only Tax, Chargeable, Income and Expense accounts
    usable = ("Tax", "Chargeable", "Income Account", "Expense Account")
    return {r.purpose: r.account for r in rows if r.account and frappe.get_cached_value("Account", r.account, "account_type") in usable}


def _template(company: str, title: str, not_applicable: list[str]) -> str | None:
    abbr = frappe.get_cached_value("Company", company, "abbr")
    name = f"{title} - {abbr}"
    if frappe.db.exists("Item Tax Template", name):
        return name
    if not not_applicable:
        return None
    doc = frappe.get_doc({
        "doctype": "Item Tax Template", "title": title, "company": company,
        "taxes": [{"tax_type": a, "tax_rate": 0, "not_applicable": 1} for a in not_applicable],
    })
    doc.flags.ignore_permissions = True
    doc.insert()
    return doc.name


def templates(company: str) -> dict:
    """{key: template name} for the company, created on first use."""
    acc = _accounts(company)
    out = {"no_vat": _template(company, NO_VAT, [acc[p] for p in VAT_PURPOSES if p in acc])}
    for kind in KINDS:
        others = [acc[f"input_vat_{k}"] for k in KINDS if k != kind and f"input_vat_{k}" in acc]
        if "input_vat_import" in acc:
            others.append(acc["input_vat_import"])
        if "output_vat" in acc:
            others.append(acc["output_vat"])
        out[kind] = _template(company, f"PH Input VAT {kind}", others)
    return out


def ours(company: str) -> set:
    return {v for v in templates(company).values() if v}


def set_line(row, template: str | None, own: set) -> None:
    current = row.get("item_tax_template")
    if current and current not in own:
        return  # chosen by a person
    if (current or None) != (template or None):
        row.item_tax_template = template


def scope_sales(doc, regime: str, line_class) -> None:
    if doc.get("is_return") and doc.get("return_against"):
        return  # a note keeps the lines (and templates) of the invoice it corrects
    t = templates(doc.company)
    own = {v for v in t.values() if v}
    for row in doc.get("items") or []:
        vat_line = regime == "VAT" and line_class(row) in ("VATable", "Government")
        set_line(row, None if vat_line else t["no_vat"], own)


def scope_purchase(doc, supplier_vat: bool, line_class, kind_of) -> None:
    if doc.get("is_return") and doc.get("return_against"):
        return
    t = templates(doc.company)
    own = {v for v in t.values() if v}
    for row in doc.get("items") or []:
        if supplier_vat and line_class(row) in ("VATable", "Government") and not flt(doc.get("ph_is_import")):
            set_line(row, t.get(kind_of(row)), own)
        else:
            set_line(row, t["no_vat"], own)
