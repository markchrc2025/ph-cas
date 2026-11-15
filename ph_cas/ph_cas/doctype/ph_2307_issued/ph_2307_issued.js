// The 2307 prints only on the BIR's own blank (January 2018 ENCS), filled the way
// the BIR forms are filled (ph_cas.forms.f2307). The toolbar Print and Ctrl+P go
// there too, so no other layout of the certificate can be printed.
function ph_print_bir_2307(frm) {
	return frappe
		.call({ method: "ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued.print_bir_form", args: { name: frm.docname }, freeze: true, freeze_message: __("Filling the BIR 2307") })
		.then((r) => {
			frm.reload_doc();
			r.message && window.open(r.message);
		});
}

frappe.ui.form.on("PH 2307 Issued", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.print_doc = () => ph_print_bir_2307(frm);
		frm.add_custom_button(__("Print on BIR form"), () => ph_print_bir_2307(frm));
	},
});
