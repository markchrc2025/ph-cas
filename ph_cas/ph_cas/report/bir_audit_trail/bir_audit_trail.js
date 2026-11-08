frappe.query_reports["BIR Audit Trail"] = {
    filters: [
        { fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
        { fieldname: "from_date", label: __("From"), fieldtype: "Datetime", default: frappe.datetime.add_days(frappe.datetime.now_datetime(), -30), reqd: 1 },
        { fieldname: "to_date", label: __("To"), fieldtype: "Datetime", default: frappe.datetime.now_datetime(), reqd: 1 },
        { fieldname: "user", label: __("User"), fieldtype: "Link", options: "User" },
        { fieldname: "ref_doctype", label: __("Document type"), fieldtype: "Link", options: "DocType" },
        { fieldname: "ref_name", label: __("Document"), fieldtype: "Data" },
        { fieldname: "sources", label: __("Sources"), fieldtype: "MultiSelect", options: "Event Log\nVersion\nDeleted Document\nAccess Log\nActivity Log", default: "Event Log, Version, Deleted Document, Access Log, Activity Log" },
    ],
};
