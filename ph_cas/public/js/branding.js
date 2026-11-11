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
					<p class="text-muted small">${frappe.utils.escape_html(b.licences)}</p>
				</div>`);
		}
		frappe.ui.misc.ph_about.show();
		return false;
	}

	$(document).on("startup", function () {
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
