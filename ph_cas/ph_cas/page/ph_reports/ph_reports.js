// B79: every report in one place, grouped, filtered by the user's modules and roles.
frappe.pages["ph-reports"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Reports"), single_column: true });
	const $body = $(page.body).addClass("sl-reports");
	$body.html(`
		<style>
			.sl-reports { padding: 8px 0 32px; }
			.sl-rep-search { max-width: 420px; margin-bottom: 16px; }
			.sl-rep-note { margin-bottom: 16px; padding: 10px 14px; border-radius: 8px; background: var(--subtle-fg); font-size: 13px; }
			.sl-rep-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
			.sl-rep-group { border: 1px solid var(--border-color); border-radius: 10px; padding: 14px 16px; background: var(--card-bg); }
			.sl-rep-group h3 { font-size: 14px; font-weight: 600; margin: 0 0 8px; }
			.sl-rep-group ul { list-style: none; padding: 0; margin: 0; }
			.sl-rep-group li { padding: 6px 0; border-top: 1px solid var(--border-color); }
			.sl-rep-group li:first-child { border-top: 0; }
			.sl-rep-group a { font-weight: 500; }
			.sl-rep-group small { display: block; color: var(--text-muted); }
		</style>
		<input class="form-control sl-rep-search" placeholder="${__("Find a report")}">
		<div class="sl-rep-note" style="display:none"></div>
		<div class="sl-rep-grid"></div>`);
	const e = frappe.utils.escape_html;
	const render = (d, q) => {
		q = (q || "").toLowerCase();
		const html = d.groups
			.map((g) => {
				const items = g.items.filter((i) => !q || (i.label + " " + i.description).toLowerCase().includes(q));
				if (!items.length) return "";
				return `<div class="sl-rep-group" data-group="${e(g.key)}"><h3>${e(g.label)}</h3><ul>${items
					.map((i) => `<li><a href="${encodeURI(i.route)}">${e(i.label)}</a><small>${e(i.description)}</small></li>`)
					.join("")}</ul></div>`;
			})
			.join("");
		$body.find(".sl-rep-grid").html(html || `<p class="text-muted">${__("No report matches.")}</p>`);
	};
	frappe.xcall("ph_cas.home.reports.catalogue").then((d) => {
		render(d);
		$body.find(".sl-rep-search").on("input", (ev) => render(d, ev.target.value));
		if (d.modules_off && d.modules_off.length) {
			const names = d.modules_off.map((m) => __(m)).join(", ");
			$body
				.find(".sl-rep-note")
				.html(
					__("Reports of switched-off modules are hidden: {0}.", [e(names)]) +
						(d.can_switch_modules ? ` <a href="/app/ph-modules">${__("Turn modules on")} &rarr;</a>` : "")
				)
				.show();
		}
	});
};
