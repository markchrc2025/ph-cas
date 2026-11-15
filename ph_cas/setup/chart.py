"""B10: the Philippine accounts a micro taxpayer's accountant expects, and the
mapping table the tax engine posts through.

The accounts are added under ERPNext's Standard chart (so an existing company
is extended, not replaced). Nothing here carries a rate."""

import frappe
from frappe import _

# purpose: parent group (Standard chart name without abbreviation), account name, account type, root type
PURPOSES = {
    "output_vat": {"parent": "Duties and Taxes", "account": "Output VAT", "account_type": "Tax", "root_type": "Liability", "description": "12% VAT on VATable sales (2550Q output tax)."},
    "output_vat_uncollected": {"parent": "Duties and Taxes", "account": "Output VAT on Uncollected Receivables", "account_type": "Tax", "root_type": "Liability", "description": "Output VAT credit on uncollected receivables and its reversal (RR 3-2024)."},
    "vat_payable": {"parent": "Duties and Taxes", "account": "VAT Payable", "account_type": "Tax", "root_type": "Liability", "description": "Net VAT due for the quarter, closed from output and input VAT."},
    "percentage_tax_payable": {"parent": "Duties and Taxes", "account": "Percentage Tax Payable", "account_type": "Tax", "root_type": "Liability", "description": "Percentage tax of a non-VAT taxpayer (2551Q)."},
    "ewt_payable": {"parent": "Duties and Taxes", "account": "Withholding Tax Payable - Expanded", "account_type": "Tax", "root_type": "Liability", "description": "Expanded withholding tax withheld from suppliers (0619-E, 1601-EQ)."},
    "wt_compensation_payable": {"parent": "Duties and Taxes", "account": "Withholding Tax Payable - Compensation", "account_type": "Tax", "root_type": "Liability", "description": "Tax withheld on compensation (1601-C), if payroll is used."},
    "final_wt_payable": {"parent": "Duties and Taxes", "account": "Withholding Tax Payable - Final", "account_type": "Tax", "root_type": "Liability", "description": "Final withholding tax (0619-F, 1601-FQ)."},
    "wt_vat_payable": {"parent": "Duties and Taxes", "account": "Withholding VAT Payable", "account_type": "Tax", "root_type": "Liability", "description": "VAT withheld or self-assessed on reverse-charge purchases (1600-VT)."},
    "income_tax_payable": {"parent": "Duties and Taxes", "account": "Income Tax Payable", "account_type": "Tax", "root_type": "Liability", "description": "Income tax due per quarter and year."},
    "input_vat_goods": {"parent": "Tax Assets", "account": "Input VAT - Goods", "account_type": "Tax", "root_type": "Asset", "description": "Input VAT on domestic purchases of goods other than capital goods."},
    "input_vat_services": {"parent": "Tax Assets", "account": "Input VAT - Services", "account_type": "Tax", "root_type": "Asset", "description": "Input VAT on domestic purchases of services."},
    "input_vat_capital": {"parent": "Tax Assets", "account": "Input VAT - Capital Goods", "account_type": "Tax", "root_type": "Asset", "description": "Input VAT on capital goods claimed in the quarter."},
    "input_vat_import": {"parent": "Tax Assets", "account": "Input VAT - Importation", "account_type": "Tax", "root_type": "Asset", "description": "Input VAT paid to the Bureau of Customs on importations."},
    "deferred_input_vat": {"parent": "Tax Assets", "account": "Deferred Input VAT", "account_type": "Tax", "root_type": "Asset", "description": "Input VAT on capital goods above the threshold, amortised (to the extent the rules still require it)."},
    "input_vat_reverse_charge": {"parent": "Tax Assets", "account": "Input VAT - Withheld on Purchases", "account_type": "Tax", "root_type": "Asset", "description": "Input VAT a VAT taxpayer may claim on VAT it remitted under reverse charge (1600-VT)."},
    "cvat_receivable": {"parent": "Tax Assets", "account": "Creditable VAT Withheld", "account_type": "Tax", "root_type": "Asset", "description": "5% VAT withheld by government customers (2307 received), credited on the 2550Q."},
    "cpt_receivable": {"parent": "Tax Assets", "account": "Creditable Percentage Tax Withheld", "account_type": "Tax", "root_type": "Asset", "description": "Percentage tax withheld by government customers, credited on the 2551Q."},
    "cwt_receivable": {"parent": "Tax Assets", "account": "Creditable Withholding Tax", "account_type": "Tax", "root_type": "Asset", "description": "Tax withheld by customers per 2307s received, credited against income tax."},
    "sc_pwd_discount": {"parent": "Direct Expenses", "account": "Senior Citizen and PWD Discounts", "account_type": "", "root_type": "Expense", "description": "20% discounts granted to senior citizens and PWDs, deductible from gross income."},
    "percentage_tax_expense": {"parent": "Indirect Expenses", "account": "Taxes and Licenses", "account_type": "", "root_type": "Expense", "description": "Percentage tax, local taxes, registration fees."},
    "income_tax_expense": {"parent": "Indirect Expenses", "account": "Income Tax Expense", "account_type": "", "root_type": "Expense", "description": "Provision for income tax."},
}


def _acc(company_abbr: str, name: str) -> str:
    return f"{name} - {company_abbr}"


def ensure_accounts(company: str) -> list[str]:
    abbr = frappe.get_cached_value("Company", company, "abbr")
    created = []
    for purpose, spec in PURPOSES.items():
        name = _acc(abbr, spec["account"])
        if frappe.db.exists("Account", name):
            continue
        parent = _acc(abbr, spec["parent"])
        if not frappe.db.exists("Account", parent):
            frappe.throw(_("Parent account {0} does not exist. The company must use ERPNext's Standard chart.").format(parent))
        acc = frappe.get_doc(
            {
                "doctype": "Account",
                "account_name": spec["account"],
                "parent_account": parent,
                "company": company,
                "account_type": spec["account_type"] or None,
                "is_group": 0,
            }
        )
        acc.flags.ignore_permissions = True
        acc.insert()
        created.append(acc.name)
    return created


def ensure_mapping(company: str) -> list[str]:
    abbr = frappe.get_cached_value("Company", company, "abbr")
    created = []
    for purpose, spec in PURPOSES.items():
        name = f"{company}-{purpose}"
        if frappe.db.exists("PH Account Mapping", name):
            continue
        frappe.get_doc(
            {"doctype": "PH Account Mapping", "company": company, "purpose": purpose, "account": _acc(abbr, spec["account"])}
        ).insert(ignore_permissions=True)
        created.append(name)
    return created


def account_for(company: str, purpose: str) -> str:
    """The account the tax engine posts to for `purpose`."""
    account = frappe.db.get_value("PH Account Mapping", {"company": company, "purpose": purpose}, "account")
    if not account:
        frappe.throw(_("No account is mapped for {0} in {1}. Run Set up Philippine company.").format(purpose, company))
    return account


@frappe.whitelist()
def setup_philippine_company(company: str) -> dict:
    """One click: accounts, mapping, BIR series for the head office. Idempotent."""
    frappe.has_permission("Company", "write", company, throw=True)
    from ph_cas.controls.serial import ensure_series

    out = {"accounts": ensure_accounts(company), "mapping": ensure_mapping(company)}
    branch = frappe.db.get_value("Company", company, "ph_branch_code") or "00000"
    out["series"] = ensure_series(company, branch)
    frappe.get_doc("Company", company).save(ignore_permissions=True)  # fills registered name and defaults
    from ph_cas.audit.events import record

    record("settings_change", "Company", company, 0, {"setup_philippine_company": out})
    if frappe.db.exists("Onboarding Step", "PH Set Up Company"):
        frappe.db.set_value("Onboarding Step", "PH Set Up Company", "is_complete", 1)  # ticks the home card step
    return out
