// B73: Philippine import templates and batch edit (after ECOUNT's Excel upload and Change Selected)
frappe.provide("ph_cas");

ph_cas.KIND_LABELS = {
	parties: __("Customers and suppliers"),
	items: __("Items"),
	balances: __("Opening account balances"),
	open_items: __("Open invoices and bills from the old books"),
};

ph_cas.import_dialog = function (opts = {}) {
	const kinds = Object.keys(ph_cas.KIND_LABELS);
	const d = new frappe.ui.Dialog({
		title: __("Import from a template"),
		size: "large",
		fields: [
			{ fieldname: "kind", fieldtype: "Select", label: __("What to import"), reqd: 1, default: opts.kind || "parties",
				options: kinds.map((k) => ({ value: k, label: ph_cas.KIND_LABELS[k] })) },
			{ fieldname: "company", fieldtype: "Link", options: "Company", label: __("Company"), default: opts.company || frappe.defaults.get_user_default("Company"),
				description: __("Opening balances and open items are dated the day before the company's go-live date.") },
			{ fieldname: "get_template", fieldtype: "Button", label: __("Download the template (CSV, opens in Excel)") },
			{ fieldname: "file", fieldtype: "Attach", label: __("Filled-in template (CSV or Excel)") },
			{ fieldname: "result", fieldtype: "HTML" },
		],
		primary_action_label: __("Import"),
		primary_action: (v) => run("run_import", v),
		secondary_action_label: __("Check the file"),
		secondary_action: () => run("check_import", d.get_values()),
	});
	d.fields_dict.get_template.$input.on("click", () => {
		window.open(`/api/method/ph_cas.imports.download_template?kind=${encodeURIComponent(d.get_value("kind"))}`);
	});
	const esc = frappe.utils.escape_html;
	function show(html) { d.fields_dict.result.$wrapper.html(html); }
	function run(method, v) {
		if (!v || !v.file) { frappe.msgprint(__("Attach the filled-in template first.")); return; }
		frappe.call({ method: `ph_cas.imports.${method}`, args: { kind: v.kind, company: v.company, file_url: v.file }, freeze: true }).then((r) => {
			const m = r.message;
			if (method === "check_import") {
				const errs = m.errors.map((x) => `<li>${__("Line {0}", [x.line])}: ${esc(x.errors.join("; "))}</li>`).join("");
				const warns = m.warnings.map((x) => `<li>${__("Line {0}", [x.line])}: ${esc(x.warnings.join("; "))}</li>`).join("");
				const sum = m.summary.map((s) => `<li>${esc(s)}</li>`).join("");
				show(`<p><b>${m.ok ? __("{0} row(s) ready to import.", [m.rows]) : __("{0} row(s) read; fix these before importing.", [m.rows])}</b></p>`
					+ (sum ? `<ul style="color:var(--red-600)">${sum}</ul>` : "")
					+ (errs ? `<ul style="color:var(--red-600)">${errs}</ul>` : "")
					+ (warns ? `<p>${__("Notes")}</p><ul style="color:var(--text-muted)">${warns}</ul>` : ""));
			} else {
				const parts = [];
				if (m.created.length) parts.push(__("{0} created", [m.created.length]));
				if (m.updated.length) parts.push(__("{0} updated", [m.updated.length]));
				if (m.posted.length) parts.push(__("posted {0}", [m.posted.join(", ")]));
				show(`<p style="color:var(--green-600)"><b>${__("Imported {0} row(s)", [m.rows])}: ${esc(parts.join(", "))}</b></p>`);
				frappe.show_alert({ message: __("Import done"), indicator: "green" });
			}
		});
	}
	d.show();
	return d;
};

ph_cas.batch_edit = function (listview) {
	const doctype = listview.doctype;
	const names = listview.get_checked_items(true);
	if (!names.length) { frappe.msgprint(__("Tick the records to change first.")); return; }
	frappe.call({ method: "ph_cas.imports.batch_fields", args: { doctype } }).then((r) => {
		const fields = r.message || [];
		const d = new frappe.ui.Dialog({
			title: __("Change {0} selected", [names.length]),
			fields: [
				{ fieldname: "field", fieldtype: "Select", label: __("Field"), reqd: 1, options: fields.map((f) => ({ value: f.fieldname, label: __(f.label) })),
					onchange: () => {
						const f = fields.find((x) => x.fieldname === d.get_value("field"));
						const w = d.fields_dict.value_wrap.$wrapper.empty();
						d.value_control = frappe.ui.form.make_control({ parent: w, df: { fieldname: "v", label: __("New value"), fieldtype: f.fieldtype, options: f.options }, render_input: true });
					} },
				{ fieldname: "value_wrap", fieldtype: "HTML" },
			],
			primary_action_label: __("Change"),
			primary_action: () => {
				const field = d.get_value("field");
				const value = d.value_control ? d.value_control.get_value() : null;
				frappe.call({ method: "ph_cas.imports.batch_update", args: { doctype, names, values: { [field]: value } }, freeze: true }).then((x) => {
					const m = x.message;
					d.hide();
					listview.refresh();
					const refused = m.refused.map((y) => `<li>${frappe.utils.escape_html(y.name)}: ${frappe.utils.escape_html(y.reason)}</li>`).join("");
					frappe.msgprint({ title: __("Batch edit"), message: __("{0} changed.", [m.changed.length]) + (refused ? `<p>${__("Refused")}</p><ul>${refused}</ul>` : "") });
				});
			},
		});
		d.show();
		if (fields.length) { d.set_value("field", fields[0].fieldname); }
	});
};

// the list buttons: wired from each list's own doctype_list_js (hooks.py), which runs after ERPNext's
ph_cas.wire_import_list = function (dt) {
	frappe.listview_settings[dt] = frappe.listview_settings[dt] || {};
	const s = frappe.listview_settings[dt];
	const base = s.onload;
	s.onload = function (listview) {
		base && base.call(this, listview);
		listview.page.add_inner_button(__("Import from a template"), () => ph_cas.import_dialog({ kind: dt === "Item" ? "items" : "parties" }));
		listview.page.add_actions_menu_item(__("Batch edit BIR fields"), () => ph_cas.batch_edit(listview), false);
	};
};
