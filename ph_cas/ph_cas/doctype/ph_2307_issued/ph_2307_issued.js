// The 2307 prints only on the BIR's own blank (January 2018 ENCS), filled the way
// the BIR forms are filled (ph_cas.forms.f2307). The toolbar Print and Ctrl+P go
// there too, so no other layout of the certificate can be printed.
// B90: printing locks the certificate (a draft is submitted first) and prints it
// clean; Mark as issued records the day it went to the supplier.
function ph_print_bir_2307(frm) {
	const go = () => ph_cas.print_2307(frm.docname, () => frm.reload_doc());  // B94: straight to the printer dialog
	if (frm.doc.docstatus === 0) {
		frappe.confirm(__("Printing locks this 2307: its figures can no longer change. To correct it later, cancel it and amend. Print now?"), () => (frm.is_dirty() ? frm.save().then(go) : go()));
		return;
	}
	return go();
}

function ph_mark_2307_issued(frm) {
	frappe.prompt(
		[{ fieldname: "issued_on", fieldtype: "Date", label: __("Handed to the supplier on"), default: frappe.datetime.get_today(), reqd: 1 }],
		(v) =>
			frappe
				.call({ method: "ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued.mark_issued", args: { name: frm.docname, issued_on: v.issued_on } })
				.then(() => frm.reload_doc()),
		__("Mark as issued"),
		__("Mark as issued")
	);
}

frappe.ui.form.on("PH 2307 Issued", {
	onload(frm) {
		// B97 (LDG-251): an amendment shows its own fresh print history before its first save
		if (frm.is_new() && frm.doc.amended_from) {
			frm.doc.status = "Draft";
			frm.doc.print_count = 0;
			frm.doc.printed_on = null;
			frm.doc.issued_on = null;
		}
	},
	refresh(frm) {
		if (frm.is_new()) return;
		frm.print_doc = () => ph_print_bir_2307(frm);
		if (frm.doc.docstatus < 2) {
			frm.add_custom_button(frm.doc.status === "Draft" || !frm.doc.status ? __("Print on BIR form") : __("Reprint on BIR form"), () => ph_print_bir_2307(frm));
		}
		if (frm.doc.docstatus === 1 && frm.doc.status === "Printed") {
			frm.add_custom_button(__("Mark as issued"), () => ph_mark_2307_issued(frm));
		}
		const colors = { Draft: "red", Printed: "orange", Issued: "green", Cancelled: "gray" };
		if (frm.doc.docstatus > 0) {
			const s = frm.doc.docstatus === 2 ? "Cancelled" : frm.doc.status === "Draft" || !frm.doc.status ? "Not printed" : frm.doc.status;
			frm.page.set_indicator(__(s), colors[s] || "blue");
		}
	},
});
