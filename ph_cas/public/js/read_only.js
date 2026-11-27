// B96 (UAT LDG-245): Staff reads bills, journals, suppliers and BIR returns but is offered no
// action on them. frappe.boot.ph_cas_read_only lists those doctypes for a Staff user; the
// permissions the forms and lists ask for are cut to read, print, email and export.
(function () {
	const ro = () => new Set((frappe.boot && frappe.boot.ph_cas_read_only) || []);
	const CUT = ["write", "create", "submit", "cancel", "amend", "delete", "import"];
	const base = frappe.perm.get_perm.bind(frappe.perm);
	frappe.perm.get_perm = function (doctype, doc) {
		const perm = base(doctype, doc);
		if (!ro().has(doctype)) return perm;
		return (perm || []).map((p) => {
			const q = Object.assign({}, p);
			CUT.forEach((k) => (q[k] = 0));
			return q;
		});
	};
	const has = frappe.perm.has_perm && frappe.perm.has_perm.bind(frappe.perm);
	if (has) {
		frappe.perm.has_perm = function (doctype, permlevel, ptype, doc) {
			if (ro().has(doctype) && CUT.includes(ptype)) return false;
			return has(doctype, permlevel, ptype, doc);
		};
	}
	$(document).on("form-refresh", (e, frm) => {
		if (!frm || !ro().has(frm.doctype)) return;
		frm.disable_save && frm.disable_save();
		frm.page.clear_primary_action && frm.page.clear_primary_action();
		frm.set_read_only && frm.set_read_only();
	});
})();
