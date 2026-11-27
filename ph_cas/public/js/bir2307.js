// B94 (owner's tests, 27 Nov 2026): the 2307 goes straight to the printer dialog, and the
// invoices show their 2307s. A bill or a payment shows the 2307 Issued it is on, with a print
// button; a sales invoice with tax withheld by the customer gets "BIR 2307" to upload the
// customer's certificate (a 2307 Received linked to the invoice, used by the income tax returns).
frappe.provide("ph_cas");

// Print a PDF at a URL in a hidden frame, as Frappe's own "print the generated PDF" does.
ph_cas.print_pdf_url = function (url) {
	return fetch(url, { credentials: "same-origin" })
		.then((r) => { if (!r.ok) throw new Error(r.statusText); return r.blob(); })
		.then((blob) => {
			const src = URL.createObjectURL(blob);
			const frame = document.createElement("iframe");
			frame.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
			frame.src = src;
			frame.onload = () => {
				try { frame.contentWindow.focus(); frame.contentWindow.print(); } catch (e) { window.open(src); }
				setTimeout(() => { frame.remove(); URL.revokeObjectURL(src); }, 60000);
			};
			document.body.appendChild(frame);
		})
		.catch(() => window.open(url));
};

ph_cas.print_2307 = function (name, after) {
	return frappe
		.call({ method: "ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued.print_bir_form", args: { name }, freeze: true, freeze_message: __("Filling the BIR 2307") })
		.then((r) => { after && after(); r.message && ph_cas.print_pdf_url(r.message); });
};

ph_cas.show_2307_issued = function (frm) {
	if (frm.is_new() || frm.doc.docstatus !== 1) return;
	frappe.xcall("ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued.for_document", { doctype: frm.doctype, name: frm.doc.name }).then((rows) => {
		(rows || []).forEach((c) => {
			const e = frappe.utils.escape_html;
			frm.dashboard.add_comment(
				`${__("BIR 2307")}: <a href="/desk/ph-2307-issued/${encodeURIComponent(c.name)}">${e(c.name)}</a> (${e(__(c.status || "Draft"))})`,
				c.status === "Issued" ? "green" : "blue", true);
			frm.add_custom_button(__("Print 2307 {0}", [c.quarter || ""]), () => ph_cas.print_2307(c.name), __("BIR 2307"));
		});
		if (!(rows || []).length && flt(frm.doc.ph_ewt_amount || frm.doc.ph_ewt_on_advance)) {
			frm.add_custom_button(__("Make the 2307"), () => frappe.xcall("ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued.make_for_document", { doctype: frm.doctype, name: frm.doc.name })
				.then((n) => frappe.set_route("Form", "PH 2307 Issued", n)), __("BIR 2307"));
		}
	});
};

ph_cas.received_2307 = function (frm) {
	if (frm.is_new() || frm.doc.docstatus !== 1) return;
	frappe.xcall("ph_cas.tax.received_2307.for_invoice", { invoice: frm.doc.name }).then((m) => {
		if (!m || !m.withheld) return;
		const e = frappe.utils.escape_html;
		if (m.received.length) {
			frm.dashboard.add_comment(`${__("BIR 2307 from the customer")}: ` + m.received.map((c) => `<a href="/desk/ph-2307-received/${encodeURIComponent(c.name)}">${e(c.name)}</a>${c.file ? " (" + __("attached") + ")" : ""}`).join(", "), "green", true);
		} else {
			frm.dashboard.add_comment(__("The customer withheld {0}. Its BIR 2307 has not been received yet.", [format_currency(m.withheld, frm.doc.currency)]), "orange", true);
		}
		frm.add_custom_button(__("Upload the customer's 2307"), () => ph_cas.upload_received_2307(frm, m), __("BIR 2307"));
	});
};

ph_cas.upload_received_2307 = function (frm, m) {
	const d = new frappe.ui.Dialog({
		title: __("Customer's BIR 2307 for {0}", [frm.doc.name]),
		fields: [
			{ fieldname: "file", fieldtype: "Attach", label: __("The 2307 (PDF or a scan)"), reqd: 1 },
			{ fieldname: "atc", fieldtype: "Data", label: __("ATC"), default: m.atc, reqd: 1 },
			{ fieldname: "income", fieldtype: "Currency", label: __("Income payment on the 2307"), default: m.base, reqd: 1 },
			{ fieldname: "tax", fieldtype: "Currency", label: __("Tax withheld on the 2307"), default: m.withheld, reqd: 1 },
			{ fieldname: "received_on", fieldtype: "Date", label: __("Received on"), default: frappe.datetime.get_today(), reqd: 1 },
		],
		primary_action_label: __("Save"),
		primary_action: (v) => frappe.xcall("ph_cas.tax.received_2307.record_for_invoice", { invoice: frm.doc.name, ...v }).then((name) => {
			d.hide();
			frappe.show_alert({ message: __("Saved as {0}", [name]), indicator: "green" });
			frm.reload_doc();
		}),
	});
	d.show();
};

frappe.ui.form.on("Purchase Invoice", { refresh: (frm) => ph_cas.show_2307_issued(frm) });
frappe.ui.form.on("Payment Entry", { refresh: (frm) => frm.doc.party_type === "Supplier" && ph_cas.show_2307_issued(frm) });
frappe.ui.form.on("Sales Invoice", { refresh: (frm) => ph_cas.received_2307(frm) });
