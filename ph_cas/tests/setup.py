"""before_tests hook: completes the ERPNext setup wizard for a Philippine
company so that tests can create accounting documents on a bare site."""

import frappe
from frappe.utils import now_datetime

TEST_COMPANY = "_Test PH Company"
TEST_ABBR = "TPC"


def before_tests():
    frappe.clear_cache()
    if frappe.db.get_single_value("System Settings", "setup_complete"):
        from ph_cas.setup.chart import setup_philippine_company

        setup_philippine_company(TEST_COMPANY)
        _incorporated(TEST_COMPANY)
        frappe.db.commit()
        return
    from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

    year = now_datetime().year
    setup_complete(
        {
            "currency": "PHP",
            "full_name": "Test User",
            "email": "test@example.com",
            "company_name": TEST_COMPANY,
            "company_abbr": TEST_ABBR,
            "timezone": "Asia/Manila",
            "country": "Philippines",
            "fy_start_date": f"{year}-01-01",
            "fy_end_date": f"{year}-12-31",
            "language": "English",
            "chart_of_accounts": "Standard",
            "setup_demo": 0,
        }
    )
    frappe.db.commit()
    frappe.clear_cache()
    from ph_cas.setup.chart import setup_philippine_company

    setup_philippine_company(TEST_COMPANY)
    frappe.db.commit()
    _incorporated(TEST_COMPANY)
    frappe.db.commit()


def _incorporated(company: str):
    """The test company is a non-individual: since 15 Nov 2026 a saved company
    with a TIN needs its date of incorporation (ph_cas.setup.master_data)."""
    if not frappe.db.get_value("Company", company, "ph_incorporation_date"):
        frappe.db.set_value("Company", company, "ph_incorporation_date", "2020-01-15", update_modified=False)
