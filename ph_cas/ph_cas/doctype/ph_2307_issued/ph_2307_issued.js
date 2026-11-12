frappe.ui.form.on("PH 2307 Issued", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Print on BIR form"), () =>
			frappe.call({ method: "ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued.print_bir_form", args: { name: frm.docname }, freeze: true }).then((r) => {
				frm.reload_doc();
				r.message && window.open(r.message);
			})
		);
	},
});
