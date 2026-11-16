// PH Tax Return: the needs checklist, the figures with their kind, and the buttons.
frappe.ui.form.on("PH Tax Return", {
	refresh(frm) {
		render_needs(frm);
		colour_lines(frm);
		render_inputs(frm);
		frm.page.clear_actions_menu && frm.page.clear_inner_toolbar();
		if (frm.is_new()) return;
		const filed = frm.doc.docstatus === 1;
		if (!filed) {
			frm.add_custom_button(__("Refresh from books"), () => call(frm, "refresh_from_books", null, (r) => {
				frappe.show_alert({ message: __("{0} figures taken from the books", [r.figures]), indicator: "green" });
			}));
			if ((frm.doc.__onload || {}).ebir_export) {
				frm.add_custom_button(__("Export for eBIRForms"), () => call(frm, "export_for_ebirforms", null, (url) => window.open(url)));
			}
		}
		if (["1601-EQ", "1604-E"].includes(frm.doc.form)) {
			frm.add_custom_button(frm.doc.form === "1601-EQ" ? __("Generate QAP (.dat)") : __("Generate alphalist (.dat)"), () =>
				call(frm, "generate_attachment", null, (name) => frappe.show_alert({ message: __("Written: {0}", [name]), indicator: "green" }))
			);
		}
		if (["2550Q", "2551Q", "1701Q", "1702Q", "1701", "1702-RT"].includes(frm.doc.form)) {
			frm.add_custom_button(__("Generate SAWT (.dat)"), () =>
				call(frm, "generate_sawt", null, (name) => frappe.show_alert({ message: __("Written: {0}", [name]), indicator: "green" }))
			);
		}
		if (frm.doc.form === "2550Q") {
			frm.add_custom_button(__("Generate SLSP (.dat)"), () =>
				call(frm, "generate_slsp", null, (r) => {
					const tie = (r.tie_out || []).length ? r.tie_out.join("<br>") : __("Totals tie out with the return.");
					frappe.msgprint({ title: __("SLSP"), message: (r.files || []).join("<br>") + "<hr>" + tie, indicator: (r.tie_out || []).length ? "orange" : "green" });
				})
			);
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


// The inputs editor: the form's typed figures and schedules as fields, written into
// the draft's data on change (one call, server recomputes). Books figures show
// read-only with their value; typing over one keeps the typed value and flags it.
function render_inputs(frm) {
	const $w = frm.fields_dict.inputs_html && frm.fields_dict.inputs_html.$wrapper;
	if (!$w || frm.is_new()) return;
	frm.call({ doc: frm.doc, method: "form_spec" }).then((r) => {
		const spec = r.message || {};
		if (!spec.built) {
			$w.html(`<div class="text-muted">${__("This form's engine is not built yet.")}</div>`);
			return;
		}
		const e = frappe.utils.escape_html;
		const data = spec.data || {};
		const filed = frm.doc.docstatus === 1;
		const dis = filed ? "disabled" : "";
		const control = (key, type, val) => {
			if (type.startsWith("select:")) {
				const opts = type.slice(7).split(",").map((o) => `<option value="${e(o)}" ${val === o ? "selected" : ""}>${e(o)}</option>`).join("");
				return `<select class="form-control input-sm sl-in" data-key="${e(key)}" ${dis}><option value=""></option>${opts}</select>`;
			}
			const cls = type === "money" ? "text-right" : "";
			return `<input class="form-control input-sm sl-in ${cls}" data-key="${e(key)}" value="${e(val == null ? "" : String(val))}" ${dis}>`;
		};
		let html = `<table class="table table-bordered table-sm sl-inputs"><thead><tr><th style="width:55%">${__("Item")}</th><th>${__("Value")}</th><th style="width:80px"></th></tr></thead><tbody>`;
		Object.keys(spec.books || {}).forEach((k) => {
			if (Array.isArray(spec.books[k])) return;
			const typed = data[k] !== spec.books[k];
			const label = (spec.labels || {})[k] || k;
			html += `<tr><td>${e(label)} <span class="text-muted small">${__("from the books")}: ${e(spec.books[k])}</span></td><td>${control(k, "money", data[k])}</td><td><span class="indicator-pill ${typed ? "orange" : "blue"}">${typed ? __("typed") : __("books")}</span></td></tr>`;
		});
		(spec.inputs || []).forEach(([key, label, type]) => {
			if (spec.books && key in spec.books) return;
			html += `<tr><td>${e(label)}</td><td>${control(key, type, data[key])}</td><td><span class="indicator-pill orange">${__("typed")}</span></td></tr>`;
		});
		html += `</tbody></table>`;
		Object.keys(spec.schedules || {}).forEach((sk) => {
			const sch = spec.schedules[sk];
			const rows = Array.isArray(data[sk]) ? data[sk] : [];
			html += `<div class="sl-sched" data-sched="${e(sk)}"><b>${e(sch.label)}</b> <span class="indicator-pill ${Array.isArray((spec.books || {})[sk]) ? "blue" : "orange"}">${Array.isArray((spec.books || {})[sk]) ? __("books") : __("typed")}</span>
				<table class="table table-bordered table-sm"><thead><tr><th>#</th>${sch.columns.map((c) => `<th>${e(c)}</th>`).join("")}<th></th></tr></thead><tbody>`;
			rows.forEach((row, i) => {
				html += `<tr data-row="${i}"><td>${i + 1}</td>${sch.columns.map((c, ci) => `<td><input class="form-control input-sm sl-cell" data-col="${e(sch.keys[ci])}" value="${e(row[sch.keys[ci]] == null ? "" : String(row[sch.keys[ci]]))}" ${dis}></td>`).join("")}<td>${filed ? "" : `<a class="sl-del" href="#">${__("remove")}</a>`}</td></tr>`;
			});
			html += `</tbody></table>${filed ? "" : `<a class="sl-add" href="#">${__("Add row")}</a>`}</div>`;
		});
		$w.html(html);
		if (filed) return;
		const write = (values) => call(frm, "set_inputs", { values: JSON.stringify(values) });
		$w.find(".sl-in").on("change", function () {
			write({ [$(this).data("key")]: $(this).val() });
		});
		const sched_values = ($s) => {
			const rows = [];
			$s.find("tbody tr").each(function () {
				const row = {};
				$(this).find(".sl-cell").each(function () {
					row[$(this).data("col")] = $(this).val();
				});
				rows.push(row);
			});
			return rows;
		};
		$w.find(".sl-cell").on("change", function () {
			const $s = $(this).closest(".sl-sched");
			write({ [$s.data("sched")]: sched_values($s) });
		});
		$w.find(".sl-add").on("click", function (ev) {
			ev.preventDefault();
			const $s = $(this).closest(".sl-sched");
			write({ [$s.data("sched")]: sched_values($s).concat([{}]) });
		});
		$w.find(".sl-del").on("click", function (ev) {
			ev.preventDefault();
			const $s = $(this).closest(".sl-sched");
			const i = $(this).closest("tr").data("row");
			write({ [$s.data("sched")]: sched_values($s).filter((_, k) => k !== i) });
		});
	});
}
