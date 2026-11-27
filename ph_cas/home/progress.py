"""B91: the "Get to know Sentire Ledger" checklist ticks itself from what the company did.

Owner (26 Nov 2026): a step is done when the work is done anywhere in Ledger, not
when its checklist link is clicked. Rules approved 25 Nov 2026 (D13):
1. Set up the company: it has a TIN and a BIR Series.
2. Choose what you use: the Modules page was saved by a user at least once.
3. Confirm your tax rules: tax rules exist and none is still in draft.
4. Print your first BIR invoice: one of its sales invoices has a print record.
5. Compute your first BIR return: a BIR return was saved for it.
6. Export the books: loose-leaf books, year-end e-books, or a book report exported.
7. Build the registration pack: the pack was downloaded for it.
Steps 1 and 4 to 7 are per company; 2 and 3 are settings of the whole site."""

import frappe

BOOK_REPORTS = (
    "PH Sales Journal",
    "PH Purchase Journal",
    "PH Cash Receipts Book",
    "PH Cash Disbursements Book",
    "PH General Journal",
    "PH General Ledger Book",
    "PH Inventory Book",
)
MODULES_KEY = "ph_modules_chosen"


def _exported(company: str, key: str) -> bool:
    return bool(
        frappe.db.sql(
            """select 1 from `tabPH Event Log` where event = 'export' and ref_doctype = 'Company'
               and ref_name = %s and details like %s limit 1""",
            (company, f'%"{key}"%'),
        )
    )


def company_setup(company: str) -> bool:
    return bool(frappe.db.get_value("Company", company, "tax_id")) and bool(frappe.db.exists("BIR Series", {"company": company}))


def modules_chosen(company: str) -> bool:
    return bool(frappe.db.get_default(MODULES_KEY))


def tax_rules_confirmed(company: str) -> bool:
    # B96 (UAT LDG-248): frappe.db.exists without a name never finds a row of a normal doctype
    return frappe.db.count("PH Tax Rule") > 0 and not frappe.db.count("PH Tax Rule", {"status": "draft"})


def invoice_printed(company: str) -> bool:
    return bool(
        frappe.db.sql(
            """select 1 from `tabPH Print Record` p join `tabSales Invoice` si on si.name = p.ref_name
               where p.ref_doctype = 'Sales Invoice' and si.company = %s limit 1""",
            company,
        )
    )


def return_computed(company: str) -> bool:
    return bool(frappe.db.exists("PH Tax Return", {"company": company, "docstatus": ["<", 2]}))


def books_exported(company: str) -> bool:
    if _exported(company, "loose_leaf_books") or _exported(company, "year_end_ebooks"):
        return True
    return bool(
        frappe.db.sql(
            """select 1 from `tabPH Event Log` where event = 'export' and ref_doctype = 'Report'
               and ref_name in %s and details like %s limit 1""",
            (BOOK_REPORTS, f'%"{company}"%'),
        )
    )


def pack_built(company: str) -> bool:
    return _exported(company, "registration_pack")


CHECKS = {
    "PH Set Up Company": company_setup,
    "PH Choose Modules": modules_chosen,
    "PH Confirm Tax Rules": tax_rules_confirmed,
    "PH First BIR Invoice": invoice_printed,
    "PH Run 2550Q": return_computed,
    "PH Export Books": books_exported,
    "PH Registration Pack": pack_built,
}


def step_done(step: str, company: str | None) -> bool | None:
    """True or False for a known step, None for a step without a rule."""
    check = CHECKS.get(step)
    if not check or not company:
        return None
    return bool(check(company))


def mark_modules_chosen():
    """Called when a user saves the Modules page (not by install, migrate or patches)."""
    if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch or frappe.flags.in_test_setup:
        return
    if frappe.session.user in ("Guest",):
        return
    frappe.db.set_default(MODULES_KEY, 1)
