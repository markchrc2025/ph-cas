// Approval chains (M5.3): the panel on every form a chain applies to, and the
// Request approval, Approve, Reject and Withdraw actions. Server: ph_cas.approvals.api.
frappe.ui.form.on("*", {
	refresh(frm) {
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
	render(frm, st) {
		frm.dashboard.parent.find(".sl-approval").remove();
		if (!st.request && (!st.applies || frm.doc.docstatus === 1)) return;
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
		if (st.applies && filed && frm.doctype === "PH Tax Return" && !frm.doc.amended_by && !open) {
			frm.add_custom_button(__("Request change"), () =>
				frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("Reason for the change"), reqd: 1 }, (v) => this.request(frm, v.reason), __("Ask for an amendment of this filed return"))
			);
		}
		if (open && req.can_decide) {
			frm.add_custom_button(__("Approve"), () => this.decide(frm, req.name, "Approved")).addClass("btn-primary");
			frm.add_custom_button(__("Reject"), () => this.decide(frm, req.name, "Rejected"));
		}
		if (open && req.can_withdraw) {
			frm.add_custom_button(__("Withdraw request"), () => frappe.call({ method: "ph_cas.approvals.api.withdraw", args: { request: req.name }, callback: () => frm.reload_doc() }));
		}
		const $body = frm.dashboard.add_section(this.html(st), __("Approval"), "custom sl-approval");
		frm.dashboard.show();
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
		frappe.prompt(
			{ fieldname: "comment", fieldtype: "Small Text", label: decision === "Rejected" ? __("Reason") : __("Comment (optional)"), reqd: decision === "Rejected" ? 1 : 0 },
			(v) =>
				frappe.call({
					method: "ph_cas.approvals.api.decide",
					args: { request, decision, comment: v.comment || "" },
					freeze: true,
					callback: () => frm.reload_doc(),
				}),
			decision === "Rejected" ? __("Reject and return to the maker") : __("Approve this step")
		);
	},
};
