frappe.query_reports["PH SC PWD Sales"] = {
    filters: [
        { fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company"), reqd: 1 },
        { fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.year_start(), reqd: 1 },
        { fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
    ],
};
