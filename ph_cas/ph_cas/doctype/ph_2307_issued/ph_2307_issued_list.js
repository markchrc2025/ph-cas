frappe.listview_settings["PH 2307 Issued"] = {
	add_fields: ["status", "docstatus"],
	get_indicator(doc) {
		const colors = { Draft: "red", Printed: "orange", Issued: "green", Cancelled: "gray" };
		const s = doc.docstatus === 2 ? "Cancelled" : doc.docstatus === 1 && (doc.status || "Draft") === "Draft" ? "Not printed" : doc.status || "Draft";
		return [__(s), colors[s] || "blue", s === "Not printed" ? "docstatus,=,1" : "status,=," + s];
	},
};
