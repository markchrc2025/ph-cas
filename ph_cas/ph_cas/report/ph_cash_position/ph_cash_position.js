frappe.query_reports["PH Cash Position"] = {
    filters: [
        { fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company"), reqd: 1 },
        { fieldname: "day", label: __("Day"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
    ],
    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (data && column.fieldname === "closing" && data.closing < 0) value = `<span style="color:var(--red-600)" title="${__("Below zero: a receipt or deposit is missing, or more was paid out than the books show came in")}">${value}</span>`;
        return data && data.bold ? `<b>${value}</b>` : value;
    },
};
