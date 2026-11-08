frappe.query_reports["PH Compliance Calendar"] = {
    filters: [
        { fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company"), reqd: 1 },
        { fieldname: "year", label: __("Year"), fieldtype: "Int", default: new Date().getFullYear(), reqd: 1 },
    ],
};
