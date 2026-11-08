app_name = "ph_cas"
app_title = "PH CAS"
app_publisher = "MCRC"
app_description = "BIR-registrable Philippine computerized accounting system on ERPNext"
app_email = "mcrc.business.solutions@gmail.com"
app_license = "gpl-3.0"
required_apps = ["frappe/erpnext"]

after_install = "ph_cas.setup.install.after_install"
after_migrate = "ph_cas.setup.install.after_migrate"

before_tests = "ph_cas.tests.setup.before_tests"

doctype_js = {"Company": "public/js/company.js"}

doc_events = {
    "*": {"on_trash": "ph_cas.controls.locks.refuse_delete"},
    "Transaction Deletion Record": {"before_insert": "ph_cas.controls.locks.refuse_insert"},
    "Repost Accounting Ledger": {"before_insert": "ph_cas.controls.locks.refuse_insert"},
    "Repost Item Valuation": {"before_insert": "ph_cas.controls.locks.refuse_insert"},
    "Accounts Settings": {"validate": "ph_cas.controls.locks.validate_accounts_settings"},
}
