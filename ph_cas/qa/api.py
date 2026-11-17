"""Staging QA (docs/STAGING.md): the QA company, the QA admin, scenarios, and a status call for the
QA connector (ph_cas.qa.mcp_server).

Everything here refuses to run unless the site is a staging site: site config `ph_staging_site: 1`
and not `ph_cas_production: 1`. The container sets those only when PH_STAGING=1.
"""

import os

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

QA_USER = "qa.admin@sentire.solutions"
QA_ROLES = (
    "System Manager", "Accounting Manager", "Accounts Manager", "Accounts User", "Sales Manager", "Sales User",
    "Purchase Manager", "Purchase User", "Stock Manager", "Stock User", "Manufacturing Manager", "Projects Manager",
    "Item Manager", "Maintenance Manager", "Quality Manager", "Support Team",
    # QA pass 4: suppliers, customers' price lists and item prices need the master-manager roles;
    # timesheets and work orders the user roles
    "Sales Master Manager", "Purchase Master Manager", "Projects User", "Manufacturing User", "Maintenance User",
)


def is_staging() -> bool:
    return bool(frappe.conf.get("ph_staging_site")) and not frappe.conf.get("ph_cas_production")


def require_staging():
    if not is_staging():
        frappe.throw(_("This works only on the staging site."), frappe.PermissionError)


# ---- the base data, created once per container and kept as the golden snapshot -------------------
def seed():
    """bench --site <staging> execute ph_cas.qa.api.seed"""
    require_staging()
    from ph_cas import demo
    from ph_cas.modules.api import catalogue, set_modules

    frappe.set_user("Administrator")
    demo.seed()  # the VAT company with an invoice, a bill and the quarter's 2550Q
    set_modules([m["key"] for m in catalogue()])  # staging tests every module
    s = frappe.get_single("PH CAS Settings")
    s.product_name = "Sentire Ledger (staging)"
    s.save()
    ensure_qa_user()
    frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 0)
    frappe.db.commit()
    return "seeded"


def ensure_qa_user():
    """The QA admin the connector signs in as. Its password is STAGING_ADMIN_PASSWORD (Dokploy)."""
    require_staging()
    password = os.environ.get("STAGING_ADMIN_PASSWORD")
    if not frappe.db.exists("User", QA_USER):
        frappe.get_doc({"doctype": "User", "email": QA_USER, "first_name": "QA", "last_name": "Admin", "send_welcome_email": 0, "user_type": "System User"}).insert(ignore_permissions=True)
    user = frappe.get_doc("User", QA_USER)
    have = {r.role for r in user.roles}
    for role in QA_ROLES:
        if role not in have and frappe.db.exists("Role", role):
            user.append("roles", {"role": role})
    user.enabled = 1
    user.flags.ignore_permissions = True
    user.save()
    if password:
        from frappe.utils.password import update_password

        update_password(QA_USER, password)
    company = frappe.get_all("Company", pluck="name", limit=1)
    if company:
        frappe.defaults.set_user_default("company", company[0], QA_USER)
    frappe.db.commit()


# ---- for the connector ----------------------------------------------------------------------------
@frappe.whitelist()
def status() -> dict:
    require_staging()
    from ph_cas.modules.api import modules_on

    import ph_cas

    try:
        erp = frappe.get_attr("erpnext.__version__")
    except Exception:
        erp = None
    return {
        "site": frappe.local.site,
        "user": frappe.session.user,
        "versions": {"ph_cas": ph_cas.__version__, "erpnext": erp, "frappe": frappe.__version__},
        "companies": frappe.get_all("Company", fields=["name", "abbr", "tax_id", "ph_vat_status"]),
        "modules_on": modules_on(),
        "counts": {dt: frappe.db.count(dt, {"docstatus": 1}) for dt in ("Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry")},
        "tax_rules": {
            "confirmed": frappe.db.count("PH Tax Rule", {"status": "confirmed"}),
            "draft": frappe.db.count("PH Tax Rule", {"status": "draft"}),
        },
        "tax_returns": frappe.db.count("PH Tax Return"),
        "scenarios": sorted(SCENARIOS),
    }


@frappe.whitelist(methods=["POST"])
def seed_scenario(scenario: str, company: str | None = None) -> dict:
    require_staging()
    frappe.only_for("System Manager")
    if scenario not in SCENARIOS:
        frappe.throw(_("Unknown scenario {0}. Choose one of: {1}").format(scenario, ", ".join(sorted(SCENARIOS))))
    company = company or frappe.defaults.get_user_default("company") or frappe.get_all("Company", pluck="name")[0]
    out = SCENARIOS[scenario](company)
    frappe.db.commit()
    return {"scenario": scenario, "company": company, **out}


# ---- scenarios ------------------------------------------------------------------------------------
def _abbr(company):
    return frappe.get_cached_value("Company", company, "abbr")


def _item(code, vat_class="VATable", group="Services"):
    if not frappe.db.exists("Item", code):
        frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": code, "item_group": group if frappe.db.exists("Item Group", group) else "All Item Groups", "stock_uom": "Nos", "is_stock_item": 0, "ph_vat_class": vat_class}).insert(ignore_permissions=True)
    return code


def _customer(name, **f):
    if not frappe.db.exists("Customer", name):
        frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": "Company", "customer_group": "Commercial" if frappe.db.exists("Customer Group", "Commercial") else "All Customer Groups", "territory": "All Territories", **f}).insert(ignore_permissions=True)
    return name


def _supplier(name, **f):
    if not frappe.db.exists("Supplier", name):
        frappe.get_doc({"doctype": "Supplier", "supplier_name": name, "supplier_type": "Company", "supplier_group": "All Supplier Groups", **f}).insert(ignore_permissions=True)
    return name


def _sales(company, customer, lines, posting_date, manual_no):
    done = frappe.db.get_value("Sales Invoice", {"company": company, "ph_manual_invoice_no": manual_no, "docstatus": 1}, "name")
    if done:
        return done  # the scenario ran before: it adds nothing twice
    a = _abbr(company)
    si = frappe.get_doc({
        "doctype": "Sales Invoice", "company": company, "customer": customer, "posting_date": posting_date, "set_posting_time": int(str(posting_date) != today()),
        "due_date": add_days(posting_date, 30), "debit_to": f"Debtors - {a}", "ph_manual_invoice_no": manual_no,
        "items": [{"item_code": code, "qty": qty, "rate": rate, "income_account": f"Sales - {a}", "cost_center": f"Main - {a}"} for code, qty, rate in lines],
    })
    si.insert(ignore_permissions=True)
    si.submit()
    return si.name


def _bill(company, supplier, lines, posting_date, bill_no):
    done = frappe.db.get_value("Purchase Invoice", {"company": company, "supplier": supplier, "bill_no": bill_no, "docstatus": 1}, "name")
    if done:
        return done
    a = _abbr(company)
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice", "company": company, "supplier": supplier, "posting_date": posting_date, "set_posting_time": int(str(posting_date) != today()),
        "due_date": add_days(posting_date, 30), "bill_no": bill_no, "bill_date": posting_date, "credit_to": f"Creditors - {a}",
        "items": [{"item_code": code, "qty": qty, "rate": rate, "expense_account": f"Administrative Expenses - {a}", "cost_center": f"Main - {a}"} for code, qty, rate in lines],
    })
    pi.insert(ignore_permissions=True)
    pi.submit()
    return pi.name


class _history:
    """Seeding only: a quarter of history needs earlier posting dates, which the posting-date lock
    refuses (documents carry the day they are posted). On a staging site the scenario lifts the
    locks for its own inserts, the way the test escape hatch does, and puts them back."""

    def __enter__(self):
        require_staging()
        self.before = frappe.local.conf.get("ph_cas_unlocked")
        frappe.local.conf["ph_cas_unlocked"] = 1

    def __exit__(self, *exc):
        if self.before is None:
            frappe.local.conf.pop("ph_cas_unlocked", None)
        else:
            frappe.local.conf["ph_cas_unlocked"] = self.before


def scenario_vat_quarter(company):
    """Three months of sales and bills in the current quarter: VATable, zero-rated and exempt sales,
    a top-withholding-agent customer, goods and professional-fee suppliers with EWT."""
    from ph_cas.tax.returns import quarter_bounds

    qs, _qe = quarter_bounds(today())
    c1 = _customer("QA Retail Corp.", ph_tin="000-901-001", ph_branch_code="00000", ph_vat_status="VAT", ph_top_withholding_agent=1, ph_registered_name="QA RETAIL CORP.", ph_address_line1="1 QA Street, Pasig City", ph_zip="1605")
    c2 = _customer("QA Exporters Inc.", ph_tin="000-901-002", ph_branch_code="00000", ph_vat_status="VAT", ph_registered_name="QA EXPORTERS INC.", ph_address_line1="2 QA Street, Cebu City", ph_zip="6000")
    s1 = _supplier("QA Supplies Corp.", ph_tin="000-902-001", ph_branch_code="00000", ph_vat_status="VAT", ph_payee_type="Non-individual", ph_ewt_category="goods", ph_registered_name="QA SUPPLIES CORP.", ph_address_line1="3 QA Street, Makati City", ph_zip="1200")
    s2 = _supplier("QA Law Office", ph_tin="000-902-002", ph_branch_code="00000", ph_vat_status="VAT", ph_payee_type="Non-individual", ph_ewt_category="professional", ph_registered_name="QA LAW OFFICE", ph_address_line1="4 QA Street, Taguig City", ph_zip="1630")
    vat, zero, exempt = _item("QA Service", "VATable"), _item("QA Export Service", "Zero-rated"), _item("QA Exempt Book", "VAT-exempt")
    made = {"sales_invoices": [], "purchase_invoices": []}
    with _history():
        _fill_quarter(company, qs, c1, c2, s1, s2, vat, zero, exempt, made)
    return made


def _fill_quarter(company, qs, c1, c2, s1, s2, vat, zero, exempt, made):
    if frappe.get_cached_value("Company", company, "ph_vat_status") != "VAT":
        zero = vat  # a non-VAT seller has no zero-rated sales (percentage tax on everything it sells)
    for m in range(3):
        d = add_days(getdate(qs), 30 * m + 5)
        if d > getdate(today()):
            break
        made["sales_invoices"].append(_sales(company, c1, [(vat, 2, 15000), (exempt, 5, 300)], d, f"QA-{d:%m}-001"))
        made["sales_invoices"].append(_sales(company, c2, [(zero, 1, 40000)], d, f"QA-{d:%m}-002"))
        made["purchase_invoices"].append(_bill(company, s1, [(vat, 1, 12000)], d, f"QA-SUP-{d:%m}"))
        made["purchase_invoices"].append(_bill(company, s2, [(vat, 1, 20000)], d, f"QA-LAW-{d:%m}"))


def scenario_non_vat_company(company):
    """A second, non-VAT company (percentage tax, 2551Q) with two sales."""
    from ph_cas.setup.chart import setup_philippine_company

    name = "QA Corner Store"
    if not frappe.db.exists("Company", name):
        frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": "QACS", "default_currency": "PHP", "country": "Philippines", "chart_of_accounts": "Standard"}).insert(ignore_permissions=True)
    frappe.db.set_value("Company", name, {"tax_id": "000-903-001", "ph_branch_code": "00000", "ph_rdo": "045", "ph_vat_status": "Non-VAT", "ph_registered_name": "QA CORNER STORE", "ph_registered_address": "12 Mabini Street\nBarangay Poblacion, Makati City", "ph_zip": "1210", "ph_incorporation_date": "2022-01-10", "ph_taxpayer_class": "Micro"}, update_modified=False)
    frappe.clear_document_cache("Company", name)
    setup_philippine_company(name)
    c = _customer("QA Walk-in Customer", ph_vat_status="Non-VAT")
    item = _item("QA Snack Pack", "VATable", "Products")
    d = today()
    made = [_sales(name, c, [(item, 20, 45)], d, f"QACS-{d}-1"), _sales(name, c, [(item, 12, 45)], d, f"QACS-{d}-2")]
    return {"company_created": name, "sales_invoices": made}


# ---- income tax: a year of history up to the last full quarter (QA pass 3) ------------------------
def _journal(company, posting_date, debit_account, credit_account, amount, remark):
    done = frappe.db.get_value("Journal Entry", {"company": company, "user_remark": remark, "docstatus": 1}, "name")
    if done:
        return done
    a = _abbr(company)
    je = frappe.get_doc({
        "doctype": "Journal Entry", "company": company, "posting_date": posting_date, "voucher_type": "Journal Entry", "user_remark": remark,
        "accounts": [
            {"account": debit_account, "debit_in_account_currency": amount, "cost_center": f"Main - {a}"},
            {"account": credit_account, "credit_in_account_currency": amount, "cost_center": f"Main - {a}"},
        ],
    })
    je.insert(ignore_permissions=True)
    je.submit()
    return je.name


def _account(company, name, parent_kind, tax_class=""):
    """An expense account under the company's Indirect Expenses group, with its income tax class."""
    a = _abbr(company)
    full = f"{name} - {a}"
    if not frappe.db.exists("Account", full):
        parent = frappe.db.get_value("Account", {"company": company, "is_group": 1, "account_name": parent_kind}, "name")
        frappe.get_doc({"doctype": "Account", "company": company, "account_name": name, "parent_account": parent, "root_type": "Expense", "report_type": "Profit and Loss"}).insert(ignore_permissions=True)
    if tax_class:
        frappe.db.set_value("Account", full, "ph_tax_class", tax_class, update_modified=False)
    return full


def _received_2307(company, customer, qs, qe, base, withheld):
    if frappe.db.exists("PH 2307 Received", {"company": company, "customer": customer, "period_from": qs, "docstatus": 1}):
        return
    frappe.get_doc({"doctype": "PH 2307 Received", "company": company, "customer": customer, "period_from": qs, "period_to": qe,
                    "lines": [{"atc": "WC160", "kind": "Income tax", "month_1": base, "tax_withheld": withheld}]}).insert(ignore_permissions=True).submit()


def _months_before_this_quarter():
    from ph_cas.tax.returns import quarter_bounds

    qs, _qe = quarter_bounds(today())
    year = getdate(today()).year
    return [m for m in range(1, 13) if getdate(f"{year}-{m:02d}-01") < getdate(qs)], year


def scenario_income_year(company):
    """Every month of the year before the current quarter, for the 1702Q, 1702-RT and 1701Q figures:
    VATable sales of 250,000, cost of sales 150,000, office expenses 50,000 and representation
    5,000 a month, and a 3,000 income tax 2307 from the customer each quarter. MCIT applies
    (operations began in 2020)."""
    from frappe.utils import get_last_day

    a = _abbr(company)
    frappe.db.set_value("Company", company, {"ph_income_tax_option": "Corporate", "ph_deduction_method": "Itemized", "ph_primary_business": "Services", "ph_operations_start_year": 2020, "ph_corp_small": 0}, update_modified=False)
    frappe.clear_document_cache("Company", company)
    c = _customer("QA Retail Corp.", ph_tin="000-901-001", ph_branch_code="00000", ph_vat_status="VAT", ph_top_withholding_agent=1, ph_registered_name="QA RETAIL CORP.", ph_address_line1="1 QA Street, Pasig City", ph_zip="1605")
    item = _item("QA Service", "VATable")
    cogs = frappe.db.get_value("Account", {"company": company, "account_type": "Cost of Goods Sold", "is_group": 0}, "name")
    office = f"Administrative Expenses - {a}"
    ear = _account(company, "Representation and Entertainment", "Indirect Expenses", "Entertainment, amusement and recreation")
    cash = f"Cash - {a}"
    months, year = _months_before_this_quarter()
    made = {"sales_invoices": [], "journal_entries": [], "months": len(months)}
    with _history():
        for m in months:
            d = getdate(f"{year}-{m:02d}-10")
            made["sales_invoices"].append(_sales(company, c, [(item, 1, 250000)], d, f"QA-IT-{m:02d}"))
            made["journal_entries"].append(_journal(company, d, cogs, cash, 150000, f"QA-IT cost of sales {m:02d}"))
            made["journal_entries"].append(_journal(company, d, office, cash, 50000, f"QA-IT office expenses {m:02d}"))
            made["journal_entries"].append(_journal(company, d, ear, cash, 5000, f"QA-IT representation {m:02d}"))
            if m % 3 == 0:
                _received_2307(company, c, getdate(f"{year}-{m - 2:02d}-01"), get_last_day(d), 150000, 3000)
    return made


def scenario_individual_year(company=None):
    """A sole proprietor (individual, non-VAT, graduated rates with OSD) with sales of 100,000 a
    month for every month of the year before the current quarter, for the 1701Q."""
    from ph_cas.setup.chart import setup_philippine_company

    name = "QA Sole Proprietor"
    if not frappe.db.exists("Company", name):
        frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": "QASP", "default_currency": "PHP", "country": "Philippines", "chart_of_accounts": "Standard"}).insert(ignore_permissions=True)
    frappe.db.set_value("Company", name, {
        "tax_id": "000-904-001", "ph_branch_code": "00000", "ph_rdo": "045", "ph_vat_status": "Non-VAT", "ph_taxpayer_type": "Individual",
        "ph_individual_type": "Single Proprietorship", "ph_last_name": "Santos", "ph_first_name": "Maria", "ph_middle_name": "Lopez",
        "ph_birthdate": "1985-03-14", "ph_civil_status": "Single", "ph_registered_name": "MARIA LOPEZ SANTOS", "ph_business_style": "SANTOS BAKESHOP",
        "ph_registered_address": "5 Mabini Street\nBarangay 2, San Juan City", "ph_zip": "1500", "ph_taxpayer_class": "Micro",
        "ph_contact_number": "09171234567", "ph_email": "qa.soleprop@example.com",
        "ph_income_tax_option": "Graduated (individual)", "ph_deduction_method": "OSD (40%)",
    }, update_modified=False)
    frappe.clear_document_cache("Company", name)
    setup_philippine_company(name)
    c = _customer("QA Walk-in Customer", ph_vat_status="Non-VAT")
    item = _item("QA Bread Tray", "VATable", "Products")
    months, year = _months_before_this_quarter()
    made = []
    with _history():
        for m in months:
            made.append(_sales(name, c, [(item, 1, 100000)], getdate(f"{year}-{m:02d}-12"), f"QASP-{m:02d}"))
    return {"company_created": name, "sales_invoices": made}


SCENARIOS = {
    "vat_quarter": scenario_vat_quarter,
    "non_vat_company": scenario_non_vat_company,
    "income_year": scenario_income_year,
    "individual_year": lambda company=None: scenario_individual_year(),
}
