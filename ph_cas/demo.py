"""Demo data for a preview site: a VAT company with one invoice to a top
withholding agent and one professional-fees bill. Dummy TINs only.
Run once: bench --site <site> execute ph_cas.demo.seed"""

import frappe
from frappe.utils import today


def seed():
    from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

    frappe.set_user("Administrator")
    if not frappe.db.get_single_value("System Settings", "setup_complete"):
        year = frappe.utils.now_datetime().year
        setup_complete({"currency": "PHP", "full_name": "Demo Admin", "email": "admin@example.com", "company_name": "Tala Trading Corporation", "company_abbr": "TTC", "timezone": "Asia/Manila", "country": "Philippines", "fy_start_date": f"{year}-01-01", "fy_end_date": f"{year}-12-31", "language": "English", "chart_of_accounts": "Standard", "setup_demo": 0})
        frappe.db.commit()
    company = frappe.db.get_value("Company", {"abbr": "TTC"}, "name") or frappe.get_all("Company", pluck="name")[0]
    from ph_cas.setup.chart import setup_philippine_company

    setup_philippine_company(company)
    frappe.db.set_value("Company", company, {"tax_id": "000-111-222", "ph_branch_code": "00000", "ph_rdo": "045", "ph_vat_status": "VAT", "ph_registered_name": "Tala Trading Corporation", "ph_business_style": "Tala Trading", "ph_accn": "ACCN-DEMO-000001", "ph_accn_date": today(), "ph_taxpayer_class": "Micro", "ph_operations_start_year": 2021}, update_modified=False)
    frappe.clear_document_cache("Company", company)
    s = frappe.get_single("PH CAS Settings")
    s.product_name = "PH CAS (demo)"
    s.provider_name = "MCRC Tax and Accounting Services"
    s.save()
    frappe.defaults.set_user_default("company", company)
    abbr = frappe.get_cached_value("Company", company, "abbr")

    def item(code, cls):
        if not frappe.db.exists("Item", code):
            frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": code, "item_group": "Services", "stock_uom": "Nos", "is_stock_item": 0, "ph_vat_class": cls}).insert(ignore_permissions=True)
        return code

    if not frappe.db.exists("Customer", "Metro Retail Stores Inc"):
        frappe.get_doc({"doctype": "Customer", "customer_name": "Metro Retail Stores Inc", "customer_type": "Company", "customer_group": "Commercial", "territory": "All Territories", "ph_tin": "000-222-333", "ph_vat_status": "VAT", "ph_top_withholding_agent": 1, "ph_registered_name": "METRO RETAIL STORES INC", "ph_address_line1": "12 Ortigas Ave, Pasig City"}).insert(ignore_permissions=True)
    if not frappe.db.exists("Supplier", "Reyes & Associates CPAs"):
        frappe.get_doc({"doctype": "Supplier", "supplier_name": "Reyes & Associates CPAs", "supplier_type": "Company", "supplier_group": "Services", "ph_tin": "000-333-444", "ph_vat_status": "VAT", "ph_payee_type": "Non-individual", "ph_registered_name": "REYES & ASSOCIATES CPAS", "ph_ewt_category": "professional"}).insert(ignore_permissions=True)
    if not frappe.db.exists("Sales Invoice", {"customer": "Metro Retail Stores Inc", "docstatus": 1}):
        si = frappe.get_doc({"doctype": "Sales Invoice", "company": company, "customer": "Metro Retail Stores Inc", "posting_date": today(), "due_date": today(), "debit_to": f"Debtors - {abbr}", "items": [
            {"item_code": item("Consulting services", "VATable"), "qty": 1, "rate": 25000, "income_account": f"Sales - {abbr}", "cost_center": f"Main - {abbr}"},
            {"item_code": item("Training manual (exempt)", "VAT-exempt"), "qty": 10, "rate": 250, "income_account": f"Sales - {abbr}", "cost_center": f"Main - {abbr}"}]}).insert()
        si.submit()
    if not frappe.db.exists("Purchase Invoice", {"supplier": "Reyes & Associates CPAs", "docstatus": 1}):
        pi = frappe.get_doc({"doctype": "Purchase Invoice", "company": company, "supplier": "Reyes & Associates CPAs", "posting_date": today(), "due_date": today(), "bill_no": "RA-2026-001", "bill_date": today(), "credit_to": f"Creditors - {abbr}", "items": [
            {"item_code": item("Consulting services", "VATable"), "qty": 1, "rate": 20000, "expense_account": f"Administrative Expenses - {abbr}", "cost_center": f"Main - {abbr}"}]}).insert()
        pi.submit()
    from ph_cas.tax.returns import get_or_create, quarter_bounds

    qs, qe = quarter_bounds(today())
    get_or_create(company, "2550Q", qs, qe)
    frappe.db.commit()
    return "seeded"
