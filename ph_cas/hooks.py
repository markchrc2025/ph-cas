app_name = "ph_cas"
app_title = "Sentire Ledger"
app_publisher = "MCRC"
app_description = "BIR-registrable Philippine computerized accounting system on ERPNext"
app_email = "mcrc.business.solutions@gmail.com"
app_license = "gpl-3.0"
required_apps = ["frappe/erpnext"]

after_install = "ph_cas.setup.install.after_install"
after_migrate = "ph_cas.setup.install.after_migrate"

before_tests = "ph_cas.tests.setup.before_tests"

doctype_js = {"Company": "public/js/company.js", "Sales Invoice": "public/js/sales_invoice.js"}

# B38 branding: the product, never the framework, is what users see (ph_cas.branding)
app_logo_url = "/assets/ph_cas/images/logo.svg"
app_include_js = ["/assets/ph_cas/js/branding.js", "/assets/ph_cas/js/approvals.js"]
app_include_css = ["/assets/ph_cas/css/sentire.css"]
boot_session = "ph_cas.branding.boot_session"
extend_bootinfo = "ph_cas.branding.extend_bootinfo"
update_website_context = "ph_cas.branding.website_context"
website_context = {
    "favicon": "/assets/ph_cas/images/favicon.ico",
    "splash_image": "/assets/ph_cas/images/logo.svg",
}

doc_events = {
    "*": {
        "on_trash": "ph_cas.controls.locks.refuse_delete",
        "before_update_after_submit": "ph_cas.controls.posted_fields.refuse_posted_field_changes",
        "validate": "ph_cas.controls.dates.validate_posting_date",
        "before_submit": "ph_cas.approvals.gate.before_submit",
        "before_print": ["ph_cas.controls.dates.refuse_draft_print", "ph_cas.invoicing.printing.before_print", "ph_cas.audit.events.on_before_print"],
        "after_insert": "ph_cas.audit.events.on_after_insert",
        "on_update": ["ph_cas.audit.events.on_update", "ph_cas.approvals.gate.on_update"],
        "on_submit": "ph_cas.audit.events.on_submit",
        "on_cancel": "ph_cas.audit.events.on_cancel",
        "on_update_after_submit": "ph_cas.audit.events.on_update_after_submit",
        "after_delete": "ph_cas.audit.events.on_trash",
    },
    "Access Log": {"after_insert": "ph_cas.audit.events.on_access_log"},
    "Accounting Period": {"validate": "ph_cas.controls.dates.validate_accounting_period"},
    "Sales Invoice": {
        "before_insert": ["ph_cas.controls.serial.clear_serial_on_copy", "ph_cas.invoicing.rules.refuse_amendment"],
        "before_validate": ["ph_cas.tax.sc_pwd.before_validate", "ph_cas.tax.vat.before_validate"],
        "validate": ["ph_cas.tax.vat.validate", "ph_cas.tax.customer_withholding.validate", "ph_cas.invoicing.rules.validate_buyer_details"],
        "before_submit": ["ph_cas.controls.serial.assign_serial", "ph_cas.invoicing.rules.validate_manual_invoice_no", "ph_cas.hosting.tiers.validate_invoice_volume"],
        "before_cancel": "ph_cas.invoicing.rules.refuse_cancel",
    },
    "Purchase Invoice": {
        "before_validate": ["ph_cas.tax.purchase.before_validate", "ph_cas.tax.reverse_charge.before_validate"],
        "validate": "ph_cas.tax.purchase.validate",
    },
    "POS Invoice": {
        "before_validate": "ph_cas.tax.vat.before_validate",
        "validate": "ph_cas.tax.vat.validate",
    },
    "Payment Entry": {
        "before_insert": "ph_cas.controls.serial.clear_serial_on_copy",
        "before_validate": ["ph_cas.tax.customer_withholding.payment_before_validate", "ph_cas.tax.purchase.payment_before_validate"],
        "before_submit": "ph_cas.controls.serial.assign_serial",
    },
    "Company": {
        "validate": ["ph_cas.controls.dates.validate_company_inventory", "ph_cas.setup.master_data.validate_company", "ph_cas.invoicing.rules.warn_eis"],
        "before_insert": "ph_cas.hosting.tiers.validate_company",
    },
    "Branch": {"before_insert": "ph_cas.hosting.tiers.validate_branch"},
    "User": {"validate": ["ph_cas.hosting.tiers.validate_user", "ph_cas.branding.set_user_workspace"]},
    "Customer": {"validate": "ph_cas.setup.master_data.validate_party"},
    "Supplier": {"validate": "ph_cas.setup.master_data.validate_party"},
    "Stock Reconciliation": {"validate": "ph_cas.controls.dates.require_manager"},
    "Transaction Deletion Record": {"before_insert": "ph_cas.controls.locks.refuse_insert"},
    "Repost Accounting Ledger": {"before_insert": "ph_cas.controls.locks.refuse_insert"},
    "Repost Item Valuation": {"before_insert": "ph_cas.controls.locks.refuse_insert"},
    "Accounts Settings": {"validate": "ph_cas.controls.locks.validate_accounts_settings"},
    "System Settings": {"validate": "ph_cas.controls.security.validate_system_settings"},
    "Activity Log": {"after_insert": ["ph_cas.controls.security.on_activity_log", "ph_cas.audit.events.on_activity_log"]},
}

override_doctype_class = {
    "Document Naming Settings": "ph_cas.controls.naming.PHDocumentNamingSettings",
}

has_permission = {
    "Accounting Period": "ph_cas.controls.dates.manager_only_permission",
    "Stock Reconciliation": "ph_cas.controls.dates.manager_only_permission",
}

# ERPNext reads this when a new Accounting Period is opened in the form: every
# posted voucher type is offered for closing (B04 forces them closed anyway).
period_closing_doctypes = [
    "Sales Invoice",
    "Purchase Invoice",
    "POS Invoice",
    "Payment Entry",
    "Journal Entry",
    "Period Closing Voucher",
    "Stock Entry",
    "Delivery Note",
    "Purchase Receipt",
    "Stock Reconciliation",
    "Landed Cost Voucher",
    "Subcontracting Receipt",
    "Asset",
    "Asset Capitalization",
    "Asset Repair",
    "Asset Value Adjustment",
    "Invoice Discounting",
    "Dunning",
    "Process Deferred Accounting",
]

on_login = "ph_cas.audit.events.on_login"
on_logout = "ph_cas.audit.events.on_logout"

scheduler_events = {
    "daily": ["ph_cas.audit.events.daily_chain_check", "ph_cas.ops.backup.scheduled_daily_backup", "ph_cas.hosting.demo_access.daily_pilot_check"],
    "hourly": ["ph_cas.ops.monitor.alert_if_needed", "ph_cas.hosting.demo_access.expire_demo_users"],
}

jinja = {
    "methods": [
        "ph_cas.audit.header.ph_header",
        "ph_cas.audit.header.ph_header_lines",
        "ph_cas.audit.header.software_name",
        "ph_cas.audit.header.software_version",
        "ph_cas.invoicing.printing.ph_attr",
    ]
}
