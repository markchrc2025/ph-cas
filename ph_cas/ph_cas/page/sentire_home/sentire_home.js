// B39: the Sentire Ledger home page. One API call feeds every card.
frappe.pages["sentire-home"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Home"), single_column: true });
	page.wrapper.find(".page-head").hide();
	wrapper.sentire_home = new SentireHome(wrapper, page);
};

frappe.pages["sentire-home"].on_page_show = function (wrapper) {
	wrapper.sentire_home && wrapper.sentire_home.refresh();
};

class SentireHome {
	constructor(wrapper, page) {
		this.page = page;
		this.$body = $(page.body).addClass("sl-home");
		this.company = null;
		this.period = this.remember("sl-home-period") || "month";
		this.render_skeleton();
		this.refresh();
	}

	remember(key, value) {
		try {
			if (value === undefined) return localStorage.getItem(key);
			localStorage.setItem(key, value);
		} catch (e) {
			return null;
		}
	}

	render_skeleton() {
		this.$body.html(`
			<div class="sl-hero">
				<div>
					<h1 class="sl-greeting"></h1>
					<p class="sl-sub"></p>
				</div>
				<div class="sl-controls">
					<select class="form-control sl-company"></select>
					<select class="form-control sl-period">
						<option value="month">${__("This month")}</option>
						<option value="last_month">${__("Last month")}</option>
						<option value="quarter">${__("This quarter")}</option>
						<option value="year">${__("This year")}</option>
						<option value="all">${__("All time")}</option>
					</select>
				</div>
			</div>
			<div class="sl-modules-off text-muted" style="display:none;margin:0 0 12px;font-size:13px"></div>
			<div class="sl-tiles"></div>
			<div class="sl-section" data-section="create"><h2>${__("Create")}</h2><div class="sl-chips"></div></div>
			<div class="sl-onboarding"></div>
			<div class="sl-approvals"></div>
			<div class="sl-section" data-section="cards"><h2>${__("Business at a glance")}</h2><div class="sl-cards"></div></div>
			<div class="sl-grid-2" data-section="chart">
				<div class="sl-card sl-chart-card"><div class="sl-card-head"><span>${__("Sales and purchases, last 12 months")}</span></div><div class="sl-chart"></div></div>
				<div class="sl-card sl-due-card"><div class="sl-card-head"><span>${__("Coming due")}</span><a href="/app/query-report/PH Compliance Calendar">${__("Calendar")} &rarr;</a></div><div class="sl-due"></div></div>
			</div>
		`);
		this.$body.find(".sl-period").val(this.period).on("change", (e) => {
			this.period = e.target.value;
			this.remember("sl-home-period", this.period);
			this.refresh();
		});
		this.$body.find(".sl-company").on("change", (e) => {
			this.company = e.target.value;
			this.refresh();
		});
	}

	refresh() {
		this.$body.addClass("sl-loading");
		return frappe
			.xcall("ph_cas.home.dashboard.get", { company: this.company, period: this.period })
			.then((d) => {
				this.data = d;
				this.company = d.company;
				this.render(d);
			})
			.finally(() => this.$body.removeClass("sl-loading"));
	}

	money(v) {
		return frappe.format(v || 0, { fieldtype: "Currency", options: this.data.currency }, { inline: true });
	}

	render(d) {
		const e = frappe.utils.escape_html;
		this.$body.find(".sl-greeting").text(`${d.greeting}, ${d.first_name}!`);
		this.$body.find(".sl-sub").text(`${__("Here is where {0} stands today.", [d.company || __("your company")])} ${d.date}`);

		const $c = this.$body.find(".sl-company").empty();
		(d.companies || []).forEach((c) => $c.append(`<option value="${e(c)}">${e(c)}</option>`));
		$c.val(d.company).toggle((d.companies || []).length > 1);

		const off = d.modules_off || [];
		this.$body.find(".sl-modules-off").toggle(!!off.length).html(off.length
			? `${__("Switched off, so hidden from every menu: {0}.", [e(off.join(", "))])} <a href="/app/ph-modules">${__("Turn modules on")} &rarr;</a>`
			: "");
		this.$body.find(".sl-tiles").html(
			d.tiles
				.map(
					(t) => `<a class="sl-tile" href="${t.route}">
						<span class="sl-tile-icon">${frappe.utils.icon(t.icon, "md")}</span><span>${__(t.label)}</span></a>`
				)
				.join("")
		);
		this.$body.find(".sl-chips").html(
			d.create_actions.map((a) => a.action
				? `<a class="sl-chip" href="#" data-action="${a.action}">${__(a.label)}</a>`
				: `<a class="sl-chip" href="${a.route}">${__(a.label)}</a>`).join("")
		);
		this.$body.find(".sl-chips [data-action]").on("click", (ev) => {
			ev.preventDefault();
			const act = ev.currentTarget.dataset.action;
			if (act === "record_expense") ph_cas.record_expense(this.company);
			if (act === "import") ph_cas.import_dialog({ company: this.company });
		});
		// B75: each role set sees its own sections
		const sections = d.sections || ["create", "onboarding", "approvals", "cards", "chart", "due"];
		this.$body.find("[data-section]").each((_i, el) => $(el).toggle(sections.includes(el.dataset.section)));
		this.$body.find(".sl-cards").closest(".sl-section").find("h2").text(d.role_set === "Staff" ? __("Today at the counter") : __("Business at a glance"));

		this.render_onboarding(d.onboarding);
		this.render_cards(d);
		this.render_chart(d.monthly || []);
		this.render_due(d.due || []);
		this.render_approvals(d.approvals || []);
	}

	render_approvals(rows) {
		const e = frappe.utils.escape_html;
		const $el = this.$body.find(".sl-approvals").empty();
		if (!rows.length) return;
		$el.html(
			`<div class="sl-card sl-approvals-card"><div class="sl-card-head"><span>${__("Awaiting your approval")}</span><a href="/app/ph-approval-request?status=Pending">${__("All requests")} &rarr;</a></div><ul class="sl-due-list">` +
				rows
					.map(
						(r) => `<li class="soon"><a href="${r.url}"><b>${e(r.document_type)} ${e(r.document_name)}</b> <span>${e(r.step_title || "")}</span>
							<span class="sl-due-when">${__("from {0}, {1}", [e(r.requested_by), frappe.datetime.prettyDate(r.requested_at)])}</span></a></li>`
					)
					.join("") +
				`</ul></div>`
		);
	}

	render_onboarding(ob) {
		const $o = this.$body.find(".sl-onboarding").empty();
		if (!ob) return;
		const e = frappe.utils.escape_html;
		const steps = ob.steps
			.map(
				(s) => `<li class="${s.done ? "done" : ""}">
					<span class="sl-check">${s.done ? frappe.utils.icon("check", "sm") : ""}</span>
					<span class="sl-step-title">${e(s.title)}</span>
					${s.video ? `<a class="sl-step-watch" data-video="${e(s.video)}" title="${__("Watch the tutorial")}">${frappe.utils.icon("play", "xs")} ${__("Watch")}${s.video_length ? ` <span>${e(s.video_length)}</span>` : ""}</a>` : ""}
					${s.done || !s.route ? "" : `<a class="sl-step-go" href="${s.route}">${e(s.action_label || __("Open"))} &rarr;</a>`}
				</li>`
			)
			.join("");
		$o.html(`<div class="sl-card">
			<div class="sl-card-head"><span>${e(ob.title)} <small>${ob.done} ${__("of")} ${ob.total} ${__("done")}</small></span>
			<button class="btn btn-xs btn-default sl-dismiss">${__("Dismiss")}</button></div>
			<ol class="sl-steps">${steps}</ol></div>`);
		$o.find(".sl-step-watch").on("click", (ev) => {
			ev.preventDefault();
			ph_cas.tutorials.open_dialog(ev.currentTarget.dataset.video);
		});
		$o.find(".sl-dismiss").on("click", () =>
			frappe.xcall("ph_cas.home.dashboard.hide_onboarding").then(() => $o.empty())
		);
	}

	card(label, value, foot, route, cls = "") {
		return `<a class="sl-card sl-stat ${cls}" href="${route}">
			<div class="sl-stat-label">${label}</div>
			<div class="sl-stat-value">${value}</div>
			<div class="sl-stat-foot">${foot || ""}</div></a>`;
	}

	render_cards(d) {
		const f = d.figures || {};
		const n = (v) => Number(v || 0).toLocaleString();
		const open_filter = (dt) => `/app/${dt}?` + encodeURIComponent("outstanding_amount") + "=" + encodeURIComponent(JSON.stringify([">", 0]));
		const drafts =
			(f.drafts && f.drafts.sales_invoice + f.drafts.purchase_invoice + f.drafts.payment_entry + f.drafts.journal_entry) || 0;
		const all = {
			sales: () => this.card(__("Sales, {0}", [d.period_label]), this.money(f.sales), __("{0} invoices issued", [n(f.invoices_issued)]), "/app/sales-invoice?docstatus=1"),
			sales_today: () => this.card(__("Sales today"), this.money(f.sales_today), __("{0} invoices issued", [n(f.invoices_today)]), "/app/sales-invoice?docstatus=1&posting_date=" + frappe.datetime.get_today()),
			purchases: () => this.card(__("Purchases, {0}", [d.period_label]), this.money(f.purchases), __("{0} bills recorded", [n(f.bills_recorded)]), "/app/purchase-invoice?docstatus=1"),
			cash: () => this.card(__("Cash and bank"), this.money(f.cash), __("balance today"), "/app/query-report/PH Cash Position"),
			receivable: () => this.card(
				__("Receivable"),
				this.money(f.receivable),
				f.overdue_receivable ? `<span class="sl-warn">${__("{0} overdue", [this.money(f.overdue_receivable)])}</span>` : __("nothing overdue"),
				open_filter("sales-invoice")
			),
			payable: () => this.card(__("Payable"), this.money(f.payable), __("open bills"), open_filter("purchase-invoice")),
			vat: () => this.card(
				__("VAT position"),
				this.money(f.vat_position),
				__("output {0}, input {1}", [this.money(f.output_vat), this.money(f.input_vat)]),
				"/app/ph-tax-return?form=2550Q"
			),
			withholding: () => this.card(__("Withholding to remit"), this.money(f.withholding_to_remit), __("EWT, compensation, final, VAT"), "/app/ph-tax-return"),
			drafts: () => this.card(
				__("Drafts waiting"),
				n(drafts),
				drafts ? __("{0} invoices, {1} bills, {2} payments, {3} journals", [n(f.drafts.sales_invoice), n(f.drafts.purchase_invoice), n(f.drafts.payment_entry), n(f.drafts.journal_entry)]) : __("all posted"),
				"/app/sales-invoice?docstatus=0",
				drafts ? "sl-attention" : ""
			),
			drafts_mine: () => this.card(__("My unposted invoices"), n(f.drafts_mine), f.drafts_mine ? __("post them before closing the counter") : __("all posted"),
				"/app/sales-invoice?docstatus=0&owner=" + encodeURIComponent(frappe.session.user), f.drafts_mine ? "sl-attention" : ""),
		};
		const cards = (d.cards || Object.keys(all)).filter((k) => all[k]).map((k) => all[k]());
		this.$body.find(".sl-cards").html(cards.join(""));
	}

	render_chart(rows) {
		const $el = this.$body.find(".sl-chart").empty();
		if (!rows.length || !rows.some((r) => r.sales || r.purchases)) {
			$el.html(`<p class="text-muted sl-empty">${__("Post a few invoices and the months fill in here.")}</p>`);
			return;
		}
		this.chart = new frappe.Chart($el[0], {
			type: "bar",
			height: 220,
			colors: ["#123A4F", "#9FD3C7"],
			data: {
				labels: rows.map((r) => r.label),
				datasets: [
					{ name: __("Sales"), values: rows.map((r) => r.sales) },
					{ name: __("Purchases"), values: rows.map((r) => r.purchases) },
				],
			},
			axisOptions: { xIsSeries: true },
			tooltipOptions: { formatTooltipY: (v) => this.money(v) },
		});
	}

	render_due(rows) {
		const e = frappe.utils.escape_html;
		const $el = this.$body.find(".sl-due").empty();
		if (!rows.length) {
			$el.html(`<p class="text-muted sl-empty">${__("No due dates yet. Set up the company to get the calendar.")}</p>`);
			return;
		}
		$el.html(
			`<ul class="sl-due-list">` +
				rows
					.map((r) => {
						const cls = r.days < 0 ? "overdue" : r.days <= 7 ? "soon" : "";
						const when = r.days < 0 ? __("{0} days overdue", [-r.days]) : r.days === 0 ? __("today") : __("in {0} days", [r.days]);
						return `<li class="${cls}"><a href="${r.route}"><b>${e(r.form)}</b> <span>${e(r.period || "")}</span>
							<span class="sl-due-when">${frappe.datetime.str_to_user(r.due)}, ${when}</span></a></li>`;
					})
					.join("") +
				`</ul>`
		);
	}
}
