// LDG-96: an issued invoice, credit note or debit note (one with a BIR serial)
// is never cancelled; the server refuses it (ph_cas.invoicing.rules.refuse_cancel).
// This keeps the Cancel button out of sight and points to the correction path.
frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (frm.doc.docstatus !== 1 || !frm.doc.bir_serial) return;
        if (frm.perm && frm.perm[0]) frm.perm[0].cancel = 0;
        frm.page.clear_secondary_action();
        frm.dashboard.set_headline(
            __("Issued with BIR serial {0}. It cannot be cancelled: correct it with a credit note or a debit note.", [frm.doc.bir_serial])
        );
    },
});

// B75 (after ECOUNT's simple input screens): the counter view. A Cashier gets only what a sale at
// the counter needs: the customer, the lines, the totals, the payment and the Philippine fields
// (buyer details, VAT, tax withheld). Everyone can switch between the counter view and the full
// form; the choice is remembered on this browser.
frappe.provide("ph_cas");
ph_cas.SI_COUNTER_FIELDS = new Set([
	"customer", "customer_name", "tax_id", "company", "posting_date", "due_date", "is_pos", "pos_profile", "is_return", "return_against",
	"update_stock", "set_warehouse", "scan_barcode", "items", "total_qty", "total", "net_total", "taxes", "total_taxes_and_charges",
	"discount_amount", "additional_discount_percentage", "grand_total", "rounding_adjustment", "rounded_total", "in_words", "outstanding_amount",
	"payments", "paid_amount", "change_amount", "remarks", "bir_serial",
]);
ph_cas.si_counter_on = function () {
	try {
		const v = localStorage.getItem("ph-si-counter-view");
		if (v !== null) return v === "1";
	} catch (e) { /* storage blocked: fall through */ }
	return frappe.boot.ph_cas_role_set === "Cashier";
};
ph_cas.si_apply_view = function (frm) {
	const on = ph_cas.si_counter_on();
	const keep = (df) => ph_cas.SI_COUNTER_FIELDS.has(df.fieldname) || (df.fieldname || "").startsWith("ph_");
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
		// a required field still empty stays in sight, or the save would point at a hidden field
		const v = frm.doc[df.fieldname];
		const k = keep(df) || (df.reqd && (v === undefined || v === null || v === ""));
		section_keeps = section_keeps || (k && !df.hidden);
		frm.toggle_display(df.fieldname, on ? (k ? !df.hidden : false) : !df.hidden);
	});
	if (section) sections.push([section, section_keeps]);
	sections.forEach(([name, keeps]) => frm.toggle_display(name, on ? keeps : !frappe.meta.get_docfield("Sales Invoice", name).hidden));
	frm.page.wrapper.toggleClass("ph-counter-view", on);
};
frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		ph_cas.si_apply_view(frm);
		frm.add_custom_button(ph_cas.si_counter_on() ? __("Full form") : __("Counter view"), () => {
			try { localStorage.setItem("ph-si-counter-view", ph_cas.si_counter_on() ? "0" : "1"); } catch (e) { /* not remembered */ }
			frm.refresh();
		});
	},
});
