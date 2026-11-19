// B75/B76 (after ECOUNT's simple input screens): the counter view of a form. A Staff user sees only what
// the counter needs; everyone can switch between the counter view and the full form, and the choice
// is remembered on this browser. A required field still empty always stays in sight.
frappe.provide("ph_cas");

ph_cas.counter_on = function (key) {
	try {
		const v = localStorage.getItem(key);
		if (v !== null) return v === "1";
	} catch (e) { /* storage blocked: fall through */ }
	return frappe.boot.ph_cas_role_set === "Staff";
};

ph_cas.counter_view = function (frm, fields, key) {
	const on = ph_cas.counter_on(key);
	const keep = (df) => fields.has(df.fieldname) || (df.fieldname || "").startsWith("ph_");
	let section = null, section_keeps = false;
	const sections = [];
	frm.meta.fields.forEach((df) => {
		if (df.fieldtype === "Tab Break") return;
		if (df.fieldtype === "Section Break") {
			if (section) sections.push([section, section_keeps]);
			section = df.fieldname; section_keeps = keep(df);
			return;
		}
		if (df.fieldtype === "Column Break") return;
		const v = frm.doc[df.fieldname];
		const k = keep(df) || (df.reqd && (v === undefined || v === null || v === ""));
		section_keeps = section_keeps || (k && !df.hidden);
		frm.toggle_display(df.fieldname, on ? (k ? !df.hidden : false) : !df.hidden);
	});
	if (section) sections.push([section, section_keeps]);
	sections.forEach(([name, keeps]) => frm.toggle_display(name, on ? keeps : !frappe.meta.get_docfield(frm.doctype, name).hidden));
	frm.add_custom_button(on ? __("Full form") : __("Counter view"), () => {
		try { localStorage.setItem(key, on ? "0" : "1"); } catch (e) { /* not remembered */ }
		frm.refresh();
	});
};
