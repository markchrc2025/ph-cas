// B75 (after ECOUNT's Help and subscription menus): Help > Get help and Help > Your plan
frappe.provide("ph_cas");

ph_cas.show_plan = function () {
	frappe.xcall("ph_cas.hosting.tiers.my_plan").then((p) => {
		const e = frappe.utils.escape_html;
		const rows = p.rows.map((r) => `<tr><td style="padding:4px 8px">${e(r.label)}</td>`
			+ `<td style="padding:4px 8px;text-align:right;${r.near ? "color:var(--orange-600);font-weight:600" : ""}">${r.used.toLocaleString()}</td>`
			+ `<td style="padding:4px 8px;color:var(--text-muted)">${r.limit ? __("of {0}", [r.limit.toLocaleString()]) : __("no limit")}</td></tr>`).join("");
		const dates = [];
		if (p.subscription_until) dates.push(`${__("Paid until")} ${frappe.datetime.str_to_user(p.subscription_until)}${p.expired ? ` <b style="color:var(--red-600)">${__("(expired)")}</b>` : ""}`);
		if (p.pilot_until) dates.push(`${__("Pilot until")} ${frappe.datetime.str_to_user(p.pilot_until)}${p.pilot_ended ? ` <b style="color:var(--red-600)">${__("(ended)")}</b>` : ""}`);
		const contact = p.support_email
			? `<a href="mailto:${e(p.support_email)}?subject=${encodeURIComponent(__("Change of plan") + ": " + window.location.hostname)}">${__("Ask {0} to change the plan", [e(p.provider)])}</a>` : "";
		frappe.msgprint({ title: __("Your plan: {0}", [e(p.tier)]), message:
			`<p>${e(p.note)}</p><table style="width:100%;margin:8px 0">${rows}</table>`
			+ (p.modules_on.length ? `<p style="color:var(--text-muted)">${__("Modules on")}: ${p.modules_on.map(e).join(", ")}</p>` : "")
			+ (dates.length ? `<p>${dates.join("<br>")}</p>` : "") + `<p>${contact}</p>` });
	});
};

ph_cas.get_help = function () {
	const b = (frappe.boot && frappe.boot.ph_cas_branding) || {};
	const route = frappe.get_route_str();
	const facts = [`${__("Site")}: ${window.location.hostname}`, `${__("User")}: ${frappe.session.user}`, `${__("Page")}: ${route}`,
		`${b.product || "Sentire Ledger"} ${b.version || ""}`].join("\n");
	const mail = b.support_email ? `mailto:${b.support_email}?subject=${encodeURIComponent(__("Help with {0}", [route]))}&body=${encodeURIComponent("\n\n---\n" + facts)}` : null;
	const d = new frappe.ui.Dialog({
		title: __("Get help"),
		fields: [{ fieldname: "body", fieldtype: "HTML" }],
	});
	const e = frappe.utils.escape_html;
	d.fields_dict.body.$wrapper.html(`
		<div class="ph-help">
			<p><a href="#" class="ph-help-videos">${frappe.utils.icon("play", "sm")} ${__("Watch the tutorials")}</a><br>
			<span style="color:var(--text-muted)">${__("Short videos, in the order a new company needs them. A form's own videos are under Help on that form.")}</span></p>
			${mail ? `<p><a href="${mail}">${frappe.utils.icon("mail", "sm")} ${__("Write to {0}", [e(b.provider || "")])}</a><br>
			<span style="color:var(--text-muted)">${__("The message starts with this page and your user, so we can look at the same thing.")}</span></p>` : ""}
			<p><a href="#" class="ph-help-copy">${frappe.utils.icon("copy", "sm")} ${__("Copy the details of this page")}</a></p>
			<pre style="font-size:11px;background:var(--subtle-fg);padding:8px;border-radius:6px">${e(facts)}</pre>
		</div>`);
	d.$wrapper.find(".ph-help-videos").on("click", (ev) => { ev.preventDefault(); d.hide(); frappe.set_route("List", "PH Tutorial Video"); });
	d.$wrapper.find(".ph-help-copy").on("click", (ev) => { ev.preventDefault(); frappe.utils.copy_to_clipboard(facts); });
	d.show();
};
