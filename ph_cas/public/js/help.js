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
			+ (dates.length ? `<p>${dates.join("<br>")}</p>` : "")
			+ `<p><a href="#" class="ph-change-plan">${__("Change plan")}</a> &middot; ${contact}</p>`
			+ `<p style="color:var(--text-muted);font-size:11px">${__("Build")} ${e(frappe.boot.ph_cas_build || "")}</p>` });
		$(".ph-change-plan").last().on("click", (ev) => { ev.preventDefault(); frappe.hide_msgprint(); ph_cas.change_plan(); });
	});
};

// B93: the Owner moves the site up or down a tier. An upgrade applies now; a downgrade at the
// end of the paid period, and only if the site already fits the smaller tier.
ph_cas.change_plan = function () {
	frappe.xcall("ph_cas.hosting.tiers.plan_options").then((p) => {
		const e = frappe.utils.escape_html;
		const d = new frappe.ui.Dialog({ title: __("Change plan"), fields: [{ fieldname: "body", fieldtype: "HTML" }] });
		const verb = { upgrade: __("Upgrade now"), downgrade: __("Downgrade at the end of the paid period") };
		const rows = p.options.map((o) => {
			let act = "";
			if (o.kind === "current") act = `<b>${__("Your plan")}</b>`;
			else if (o.kind === "contact") act = `<span style="color:var(--text-muted)">${__("Write to us from Help > Get help")}</span>`;
			else if (!p.can_change) act = `<span style="color:var(--text-muted)">${__("Only the Owner can change the plan")}</span>`;
			else if (o.misfits.length) act = `<span style="color:var(--orange-600)">${__("Not yet:")}<br>${o.misfits.map(e).join("<br>")}</span>`;
			else act = `<button class="btn btn-xs btn-${o.kind === "upgrade" ? "primary" : "default"} ph-tier" data-tier="${e(o.tier)}" data-kind="${o.kind}">${verb[o.kind]}</button>`;
			return `<tr><td style="padding:6px 8px;vertical-align:top"><b>${e(o.tier)}</b><br><span style="color:var(--text-muted)">${e(o.note)}</span></td><td style="padding:6px 8px;vertical-align:top;text-align:right">${act}</td></tr>`;
		}).join("");
		const sched = p.scheduled_tier
			? `<p style="color:var(--orange-600)">${__("Moving to {0} on {1}.", [e(p.scheduled_tier), frappe.datetime.str_to_user(p.scheduled_tier_on)])} ${p.can_change ? `<a href="#" class="ph-cancel-down">${__("Cancel this")}</a>` : ""}</p>` : "";
		d.fields_dict.body.$wrapper.html(`${sched}<table style="width:100%">${rows}</table>
			<p style="color:var(--text-muted);font-size:11px">${__("An upgrade applies straight away and its fee starts today. A downgrade applies at the end of the period you have paid for.")}</p>`);
		d.$wrapper.find(".ph-tier").on("click", function () {
			const t = $(this).data("tier"), k = $(this).data("kind");
			const msg = k === "upgrade" ? __("Upgrade to {0} now? The new fee starts today.", [t]) : __("Move down to {0} at the end of the paid period?", [t]);
			frappe.confirm(msg, () => frappe.xcall("ph_cas.hosting.tiers.change_tier", { tier: t }).then((r) => {
				d.hide();
				frappe.show_alert({ message: r.applied ? __("You are now on {0}.", [r.tier]) : __("Moving to {0} on {1}.", [r.scheduled_tier, frappe.datetime.str_to_user(r.scheduled_tier_on)]), indicator: "green" });
			}));
		});
		d.$wrapper.find(".ph-cancel-down").on("click", (ev) => { ev.preventDefault(); frappe.xcall("ph_cas.hosting.tiers.cancel_downgrade").then(() => { d.hide(); ph_cas.change_plan(); }); });
		d.show();
	});
};

ph_cas.get_help = function () {
	const b = (frappe.boot && frappe.boot.ph_cas_branding) || {};
	const route = frappe.get_route_str();
	const facts = [`${__("Site")}: ${window.location.hostname}`, `${__("User")}: ${frappe.session.user}`, `${__("Page")}: ${route}`,
		`${b.product || "Sentire Ledger"} ${__("build")} ${frappe.boot.ph_cas_build || b.version || ""}`].join("\n");
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

// B86 (LDG-240, LDG-242): in this desk the Help row sits in the menu under the product name at
// the top of the sidebar; the apps screen's avatar menu gets Get help and Your plan too, and the
// framework's "Frappe Support" link (an outside support desk) is taken off it.
$(document).on("desktop_screen", (e, data) => {
	const desktop = data && data.desktop;
	if (!desktop || !desktop.desktop_menu_items) return;
	const add = (item) => {
		if (!desktop.desktop_menu_items.find((i) => i.label === item.label)) desktop.desktop_menu_items.push(item);
	};
	add({ icon: "circle-help", label: __("Get help"), onclick: () => ph_cas.get_help(), order: 35 });
	add({ icon: "receipt", label: __("Your plan"), onclick: () => ph_cas.show_plan(), order: 36 });
});
(function hide_outside_support() {
	const drop = () =>
		document.querySelectorAll(".dropdown-menu a, .dropdown-menu button, .dropdown-item, [role=menuitem]").forEach((el) => {
			if ((el.textContent || "").trim() === __("Frappe Support")) (el.closest("li, [role=menuitem]") || el).remove();
		});
	let queued = false;
	new MutationObserver(() => {
		if (queued) return;
		queued = true;
		requestAnimationFrame(() => {
			queued = false;
			drop();
		});
	}).observe(document.body || document.documentElement, { childList: true, subtree: true });
})();
