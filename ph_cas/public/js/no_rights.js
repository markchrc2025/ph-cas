// B82 (LDG-168, 187, 193, 206): a role that cannot add or change a record is told so on the
// form itself, before any typing, instead of meeting a refusal only when it saves.
frappe.ui.form.on("*", {
	refresh(frm) {
		const dt = frm.doctype;
		if (!dt || (frappe.boot.ph_cas_user || {}).provider_staff) return;
		const meta = frappe.get_meta(dt) || {};
		if (meta.issingle || meta.istable) return;
		let msg = null;
		if (frm.is_new() && !frappe.model.can_create(dt)) {
			msg = __("Your role cannot add new {0} records. Nothing here will be saved. Ask an Accounting Manager or the Owner.", [__(dt)]);
		} else if (!frm.is_new() && frm.doc.docstatus === 0 && !frappe.model.can_write(dt) && frm.perm && frm.perm[0] && !frm.perm[0].write) {
			msg = __("Your role can read this {0} but not change it.", [__(dt)]);
		}
		if (!msg) return;
		frm.set_intro(msg, "orange");
		if (frm.is_new()) {
			frm.disable_save();
			frm.page.clear_primary_action && frm.page.clear_primary_action();
		}
	},
});
