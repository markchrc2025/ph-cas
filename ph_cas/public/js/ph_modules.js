// PH Modules (Settings > Modules): picking an industry offers its starting set (ph_cas.modules)
frappe.ui.form.on("PH Modules", {
	industry(frm) {
		if (!frm.doc.industry) return;
		frappe.confirm(
			__("Switch on the modules for {0}? The other optional modules are switched off. You can change any switch afterwards.", [
				__(frm.doc.industry),
			]),
			() =>
				frappe
					.call({ method: "ph_cas.modules.api.apply_preset", args: { industry: frm.doc.industry }, freeze: true })
					.then(() => {
						frappe.show_alert({ message: __("Modules updated. Reloading the menus..."), indicator: "green" });
						setTimeout(() => window.location.reload(), 900);
					})
		);
	},
	after_save() {
		frappe.show_alert({ message: __("Modules updated. Reloading the menus..."), indicator: "green" });
		setTimeout(() => window.location.reload(), 900);
	},
});
