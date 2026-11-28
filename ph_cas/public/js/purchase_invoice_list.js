// B72: the Record an expense button on the Purchase Invoice list (ERPNext's own onload still runs)
(() => {
	const settings = (frappe.listview_settings["Purchase Invoice"] = frappe.listview_settings["Purchase Invoice"] || {});
	const base = settings.onload;
	settings.onload = function (listview) {
		base && base.call(this, listview);
		// B97 (UAT LDG-183, retest 6): only for a role that may post bills (not Staff, who reads them)
		if (!frappe.model.can_create("Purchase Invoice")) return;
		listview.page.add_inner_button(__("Record an expense"), () => ph_cas.record_expense());
	};
})();
