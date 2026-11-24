// Approval chains (M5.3): the panel on every form a chain applies to, and the
// Request approval, Approve, Reject and Withdraw actions. Server: ph_cas.approvals.api.
frappe.ui.form.on("*", {
	refresh(frm) {
		ph_cas_approvals.clear(frm);
		if (frm.is_new() || !frm.doc.name || frm.doctype.startsWith("PH Approval")) return;
		if (frm.doc.docstatus === 2) return;
		frappe.call({
			method: "ph_cas.approvals.api.status",
			args: { doctype: frm.doctype, name: frm.doc.name },
			callback: (r) => r.message && ph_cas_approvals.render(frm, r.message),
		});
	},
});

const ph_cas_approvals = {
	// B86 (LDG-236, 237): the panel is drawn at the top of the form's own layout, not in the
	// dashboard, which Frappe resets or hides after this call can return; its actions are buttons
	// in the panel as well as in the toolbar.
	host(frm) {
		return (frm.layout && frm.layout.wrapper) || frm.$wrapper.find(".form-layout");
	},
	clear(frm) {
		$(this.host(frm)).find(".sl-approval-panel").remove();
		frm.dashboard && frm.dashboard.parent && frm.dashboard.parent.find(".sl-approval").remove();
	},
	render(frm, st) {
		this.clear(frm);
		if (!st.request && !st.applies) return;
		const actions = [];
		const req = st.request;
		const open = req && req.status === "Pending";
		const filed = frm.doc.docstatus === 1;
		if (st.applies && !st.single_user && !filed) {
			if (!req || ["Rejected", "Withdrawn", "Void"].includes(req.status)) {
				frm.page.set_primary_action(__("Request approval"), () => this.request(frm));
			} else if (open) {
				frm.page.clear_primary_action();
			}
		}
		// B84: a Cancel chain: the posted document is cancelled through a request
		if (st.applies && filed && st.action === "Cancel" && !st.single_user) {
			frm.page.clear_secondary_action();
			if (!open) {
				const ask = () => this.ask_reason(__("Reason for the cancellation"), __("Ask for this document to be cancelled"), (reason) => this.request(frm, reason));
				frm.add_custom_button(__("Request cancellation"), ask);
				actions.push([__("Request cancellation"), ask, "btn-primary"]);
			}
		}
		if (st.applies && filed && frm.doctype === "PH Tax Return" && !frm.doc.amended_by && !open) {
			frm.add_custom_button(__("Request change"), () =>
				frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("Reason for the change"), reqd: 1 }, (v) => this.request(frm, v.reason), __("Ask for an amendment of this filed return"))
			);
		}
		if (open && req.can_decide) {
			const approve = () => this.decide(frm, req.name, "Approved");
			const reject = () => this.decide(frm, req.name, "Rejected");
			frm.add_custom_button(__("Approve"), approve).addClass("btn-primary");
			frm.add_custom_button(__("Reject"), reject);
			actions.push([__("Approve"), approve, "btn-primary"], [__("Reject"), reject, "btn-default"]);
		}
		if (open && req.can_withdraw) {
			const withdraw = () => frappe.call({ method: "ph_cas.approvals.api.withdraw", args: { request: req.name }, callback: () => frm.reload_doc() });
			frm.add_custom_button(__("Withdraw request"), withdraw);
			actions.push([__("Withdraw request"), withdraw, "btn-default"]);
		}
		const $panel = $(`<div class="sl-approval-panel form-dashboard-section" style="margin:12px 0;padding:12px 16px;border:1px solid var(--border-color);border-radius:var(--border-radius-md, 8px);background:var(--card-bg)">
			<div style="font-weight:600;margin-bottom:6px">${__("Approval")}</div>${this.html(st)}<div class="sl-approval-actions"></div></div>`);
		for (const [label, fn, cls] of actions) {
			$(`<button class="btn btn-xs ${cls}" style="margin-right:6px">${frappe.utils.escape_html(label)}</button>`).on("click", fn).appendTo($panel.find(".sl-approval-actions"));
		}
		$(this.host(frm)).prepend($panel);
	},
	// B86 (LDG-233): a prompt that never marks the reason required on the page; the server says
	// what is missing ("Give the reason for the rejection.")
	ask_reason(label, title, done, optional) {
		const d = new frappe.ui.Dialog({ title, fields: [{ fieldname: "reason", fieldtype: "Small Text", label, reqd: 0 }] });
		d.set_primary_action(__("Submit"), () => {});
		d.get_primary_btn().off("click").on("click", () => {
			const v = (d.get_value("reason") || "").trim();
			d.hide();
			done(v);
		});
		d.show();
	},
	html(st) {
		const req = st.request;
		const esc = frappe.utils.escape_html;
		let h = "";
		if (st.applies) h += `<p class="text-muted">${__("Chain: {0}", [esc(st.chain_title || st.chain)])}${st.single_user ? " " + __("(single user: you post your own documents)") : ""}</p>`;
		if (!req) return h + `<p>${__("No request yet.")}</p>`;
		const color = { Pending: "orange", Approved: "green", Consumed: "green", Rejected: "red", Withdrawn: "grey", Void: "grey" }[req.status] || "grey";
		h += `<p><span class="indicator-pill ${color}">${__(req.status === "Consumed" ? "Approved and posted" : req.status)}</span> ${__("requested by {0} on {1}", [esc(req.requested_by), frappe.datetime.str_to_user(req.requested_at)])}${req.reason ? `<br><span class="text-muted">${esc(req.reason)}</span>` : ""}</p>`;
		h += `<table class="table table-sm table-borderless sl-approval-steps"><tbody>`;
		for (const s of req.steps) {
			const rows = s.decisions.length
				? s.decisions.map((d) => {
						const c = { Approved: "green", Rejected: "red", Pending: "orange", Notified: "blue", Waiting: "grey", Skipped: "grey" }[d.decision] || "grey";
						return `<div><span class="indicator ${c}">${__(d.decision)}</span> ${esc(d.recipient || "")}${d.decided_at ? ` <span class="text-muted">${frappe.datetime.str_to_user(d.decided_at)}</span>` : ""}${d.comment ? `<br><span class="text-muted">${esc(d.comment)}</span>` : ""}</div>`;
				  }).join("")
				: `<span class="text-muted">${__("not reached")}</span>`;
			h += `<tr class="${s.current ? "sl-current" : ""}"><td style="width:2.5em"><b>${s.step}</b></td><td><b>${esc(s.title)}</b> <span class="text-muted">${__(s.role_type)}, ${__(s.receiving_order)}</span>${s.private_note ? `<br><i>${esc(s.private_note)}</i>` : ""}</td><td>${rows}</td></tr>`;
		}
		return h + `</tbody></table>`;
	},
	request(frm, reason) {
		frappe.call({
			method: "ph_cas.approvals.api.request",
			args: { doctype: frm.doctype, name: frm.doc.name, reason: reason || "" },
			freeze: true,
			callback: () => {
				frappe.show_alert({ message: __("Sent for approval"), indicator: "green" });
				frm.reload_doc();
			},
		});
	},
	decide(frm, request, decision) {
		this.ask_reason(
			decision === "Rejected" ? __("Reason") : __("Comment (optional)"),
			decision === "Rejected" ? __("Reject and return to the maker") : __("Approve this step"),
			(comment) =>
				frappe.call({
					method: "ph_cas.approvals.api.decide",
					args: { request, decision, comment },
					freeze: true,
					callback: () => frm.reload_doc(),
				})
		);
	},
};
