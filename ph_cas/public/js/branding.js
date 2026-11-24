// B38: the About dialog and small desk touches say the product, never the framework.
// Licences stay visible (GPL v3 / MIT), as the licences require.
(function () {
	function brand() {
		return (frappe.boot && frappe.boot.ph_cas_branding) || {
			product: "Sentire Ledger",
			provider: "",
			support_email: "",
			version: "",
			wordmark: "/assets/ph_cas/images/wordmark.svg",
			licences: "",
		};
	}

	// B86 (LDG-239): the About of this product also names the framework under it
	function fw_version() {
		const v = (frappe.boot.versions && frappe.boot.versions.frappe) || "";
		const m = /Sentire Framework v?([^ )]+)/.exec(brand().licences || "");
		return m ? m[1] : v;
	}

	function show_about() {
		const b = brand();
		if (!frappe.ui.misc.ph_about) {
			frappe.ui.misc.ph_about = new frappe.ui.Dialog({ title: __("About {0}", [b.product]) });
			const support = b.support_email
				? `<p>${__("Support")}: <a href="mailto:${b.support_email}">${b.support_email}</a></p>`
				: "";
			$(frappe.ui.misc.ph_about.body).html(`
				<div style="padding:4px 0 8px">
					<img src="${b.wordmark}" alt="${frappe.utils.escape_html(b.product)}" style="height:40px;margin-bottom:12px">
					<p><b>${frappe.utils.escape_html(b.product)}</b> ${__("version")} ${frappe.utils.escape_html(b.version || "")}</p>
					<p>${__("A BIR-registrable computerized accounting system for Philippine businesses.")}</p>
					${b.provider ? `<p>${__("Operated by")} ${frappe.utils.escape_html(b.provider)}</p>` : ""}
					${support}
					<hr>
					<div style="display:flex;align-items:center;gap:12px;margin:8px 0">
						<img src="/assets/frappe/images/frappe-comp-logo.svg" alt="Sentire Framework" style="height:32px">
						<div>
							<div class="small">${__("Sentire Framework, based on Frappe Framework (MIT).")}</div>
							<div class="small"><b>${__("Sentire Framework Version")}</b>: ${frappe.utils.escape_html(fw_version())}</div>
						</div>
					</div>
					<p class="text-muted small">${frappe.utils.escape_html(b.licences)}</p>
				</div>`);
		}
		frappe.ui.misc.ph_about.show();
		return false;
	}

	// Hover peek on the collapsed icon rail (see sentire.css). A short delay on both sides
	// keeps a pointer crossing the rail from flapping it open and shut.
	function setup_rail_peek() {
		const $container = $(".body-sidebar-container");
		if (!$container.length || $container.data("sl-peek-bound")) return;
		$container.data("sl-peek-bound", true);
		let timer = null;
		const rail = () => !$container.hasClass("expanded") && !$container.hasClass("sidebar-hidden");
		$container.on("mouseenter", ".body-sidebar", () => {
			if (!rail() || frappe.is_mobile()) return;
			clearTimeout(timer);
			timer = setTimeout(() => $container.addClass("sl-peek"), 120);
		});
		$container.on("mouseleave", ".body-sidebar", () => {
			clearTimeout(timer);
			timer = setTimeout(() => $container.removeClass("sl-peek"), 200);
		});
		// a click that navigates or toggles folds the peek at once
		$container.on("click", ".body-sidebar .item-anchor, .sidebar-collapse-arrow", () => $container.removeClass("sl-peek"));
	}

	// The dock (the column of shell icons) names its tiles on hover: the labels fly out beside
	// the tiles over the page, so nothing reflows (see sentire.css).
	function setup_dock_peek() {
		const $dock = $("#desk-dock");
		if (!$dock.length || $dock.data("sl-peek-bound")) return;
		$dock.data("sl-peek-bound", true);
		let timer = null;
		$dock.on("mouseenter", () => {
			if (!$("body").hasClass("dock-pinned") || frappe.is_mobile()) return;
			clearTimeout(timer);
			timer = setTimeout(() => $dock.addClass("sl-dock-peek"), 150);
		});
		$dock.on("mouseleave", () => {
			clearTimeout(timer);
			timer = setTimeout(() => $dock.removeClass("sl-dock-peek"), 150);
		});
		$dock.on("click", ".dock-item", () => $dock.removeClass("sl-dock-peek"));
	}

	$(document).on("startup", function () {
		setup_rail_peek();
		setup_dock_peek();
		// the dock is built after startup on some routes
		setTimeout(setup_dock_peek, 1500);
		frappe.ui.misc.about = show_about;
		frappe.ui.toolbar.show_about = show_about;
		// B39: Frappe can only land on a workspace; the product lands on its home page.
		const home = frappe.boot.ph_cas_branding && frappe.boot.ph_cas_branding.home;
		if (home && home.workspace_path && home.page) {
			const here = window.location.pathname.replace(/\/$/, "");
			if (here === home.workspace_path && !window.location.search && !window.location.hash) {
				frappe.set_route(home.page);
			}
		}
	});

	// the toolbar may be built before "startup"; patch now too
	if (frappe.ui && frappe.ui.toolbar) {
		frappe.ui.toolbar.show_about = show_about;
	}
	if (frappe.ui && frappe.ui.misc) {
		frappe.ui.misc.about = show_about;
	}
})();
