// PH Tax Return: the needs checklist, the figures with their kind, and the buttons.
frappe.ui.form.on("PH Tax Return", {
	refresh(frm) {
		render_needs(frm);
		colour_lines(frm);
		frm.page.clear_actions_menu && frm.page.clear_inner_toolbar();
		if (frm.is_new()) return;
		const filed = frm.doc.docstatus === 1;
		if (!filed) {
			frm.add_custom_button(__("Refresh from books"), () => call(frm, "refresh_from_books", null, (r) => {
				frappe.show_alert({ message: __("{0} figures taken from the books", [r.figures]), indicator: "green" });
			}));
			frm.add_custom_button(__("Export for eBIRForms"), () => call(frm, "export_for_ebirforms", null, (url) => window.open(url)));
		}
		frm.add_custom_button(filed ? __("Clear copy (as filed)") : __("Preview (DRAFT)"), () =>
			call(frm, "preview", null, (url) => url && window.open(url))
		);
		if (!filed && !frm.doc.confirmation) {
			frm.add_custom_button(__("Attach BIR confirmation"), () => attach_confirmation(frm));
		}
		if (filed && !frm.doc.amended_by) {
			frm.add_custom_button(__("Open amendment"), () =>
				frappe.prompt(
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason for the amendment"), reqd: 1 },
					(v) => call(frm, "open_amendment", { reason: v.reason }, (name) => frappe.set_route("Form", "PH Tax Return", name)),
					__("Open an amendment of this filed return")
				)
			);
		}
		if (frm.doc.export_file) frm.add_custom_button(__("eBIRForms file"), () => window.open(frm.doc.export_file), __("Files"));
		if (frm.doc.clear_copy) frm.add_custom_button(__("Clear copy"), () => window.open(frm.doc.clear_copy), __("Files"));
		frm.set_intro("");
		if (filed) frm.set_intro(__("Filed {0}, reference {1}. A filed return is never changed; a manager opens an amendment.", [frappe.datetime.str_to_user(frm.doc.filed_on), frm.doc.filed_reference || ""]), "green");
		else if (frm.doc.status === "Ready") frm.set_intro(__("Nothing missing. Attach the BIR confirmation and submit to mark it filed."), "blue");
	},
	data(frm) {
		frm.dirty();
	},
});

function call(frm, method, args, then) {
	return frm.call({ doc: frm.doc, method, args: args || {}, freeze: true }).then((r) => {
		frm.reload_doc();
		then && then(r.message);
	});
}

function render_needs(frm) {
	let needs = [];
	try {
		needs = typeof frm.doc.needs === "string" ? JSON.parse(frm.doc.needs || "[]") : frm.doc.needs || [];
	} catch (e) {
		needs = [];
	}
	const e = frappe.utils.escape_html;
	let html;
	if (!needs.length) {
		html = `<div class="text-muted">${__("Nothing missing.")}</div>`;
	} else {
		html =
			`<ul class="sl-needs">` +
			needs
				.map((n) => {
					const link = n.set_with && n.set_with.doctype !== "PH Tax Return" ? `<a href="/app/${frappe.router.slug(n.set_with.doctype)}/${encodeURIComponent(n.set_with.name)}">${__("Open {0}", [e(n.set_with.doctype)])} &rarr;</a>` : "";
					return `<li><b>${e(n.question)}</b> <span class="text-muted">${e(n.why)}</span> ${link}</li>`;
				})
				.join("") +
			`</ul>`;
	}
	frm.fields_dict.needs_html.$wrapper.html(html);
}

function colour_lines(frm) {
	const grid = frm.fields_dict.lines && frm.fields_dict.lines.grid;
	if (!grid) return;
	setTimeout(() => {
		(grid.grid_rows || []).forEach((row) => {
			const kind = row.doc.source;
			const colour = kind === "books" ? "blue" : kind === "typed" ? "orange" : "gray";
			const $cell = row.row.find('[data-fieldname="source"] .static-area');
			if ($cell.length) $cell.html(`<span class="indicator-pill ${colour}">${__(kind || "")}</span>`);
		});
	}, 100);
}

function attach_confirmation(frm) {
	new frappe.ui.FileUploader({
		doctype: frm.doctype,
		docname: frm.docname,
		fieldname: "confirmation_upload",
		restrictions: { allowed_file_types: [".eml", ".pdf", ".txt"] },
		on_success(file) {
			frappe.call({
				method: "ph_cas.ph_cas.doctype.ph_tax_return.ph_tax_return.attach_confirmation",
				args: { tax_return: frm.docname, file_url: file.file_url },
				freeze: true,
			}).then((r) => {
				const m = r.message || {};
				if (m.errors && m.errors.length) {
					frappe.msgprint({ title: __("The confirmation does not match"), message: m.errors.join("<br>"), indicator: "red" });
				} else {
					frappe.show_alert({ message: __("Confirmation {0} attached (received {1})", [m.file_name || "", m.received_at || ""]), indicator: "green" });
				}
				frm.reload_doc();
			});
		},
	});
}
