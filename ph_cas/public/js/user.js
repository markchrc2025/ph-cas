// B82 (LDG-166, 170): the Owner manages users by role set. The raw role list and the
// provider box are system areas; they show only to the Administrator and provider staff.
frappe.ui.form.on("User", {
	refresh(frm) {
		const system = frappe.session.user === "Administrator" || (frappe.boot.ph_cas_user || {}).provider_staff;
		const has_set = (frm.doc.role_profiles || []).length || frm.doc.role_profile_name;
		frm.toggle_display(["roles_html", "sb_allow_modules", "modules_html", "module_profile"], !!system || !has_set);
		if (!system) {
			frm.set_df_property("ph_provider_staff", "read_only", 1);
			frm.toggle_display("ph_provider_staff", false);
			if (has_set) frm.toggle_display("sb1", true);
		}
	},
});
