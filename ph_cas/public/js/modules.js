// M5.2 module toggles (ph_cas.modules). The menus, sidebars and search bar are already pruned in
// the boot; this file covers what the boot cannot:
// 1. a route to a switched-off module (a bookmark, a link in an old email) shows a notice and
//    goes Home instead of opening;
// 2. the onboarding guides leave out the steps of switched-off modules.
frappe.provide("ph_cas.modules");

(function () {
	const M = ph_cas.modules;
	const info = () => (frappe.boot && frappe.boot.ph_modules) || { off: [] };
	const has = (list, x) => (info()[list] || []).includes(x);

	M.blocked = function (route) {
		route = route || frappe.get_route() || [];
		const [kind, name] = route;
		if (!info().off.length) return null;
		if (!name) return M.blocked_slug(route);
		if (["List", "Form", "Tree", "Report", "print", "Calendar", "Kanban", "Gantt", "Image", "Dashboard"].includes(kind) && has("doctypes", name))
			return name;
		if (kind === "query-report" && has("reports", name)) return name;
		if (kind === "Workspaces" && has("workspaces", name)) return name;
		return null;
	};

	// A doctype that is hidden from the boot no longer resolves by its slug, so /app/stock-entry
	// arrives as ["stock-entry"]; match the slug back to the doctype.
	M.blocked_slug = function (route) {
		route = route || frappe.get_route() || [];
		if (!info().off.length || !route[0]) return null;
		const slug = String(route[0]).toLowerCase();
		const slugify = (n) => n.toLowerCase().replace(/ /g, "-");
		return (info().doctypes || []).find((d) => slugify(d) === slug) || (info().workspaces || []).find((w) => slugify(w) === slug) || null;
	};

	function notice(what) {
		frappe.msgprint({
			title: __("This module is switched off"),
			indicator: "orange",
			message:
				__("{0} belongs to a module that is switched off for this business.", [__(what)]) +
				" " +
				(frappe.user.has_role("System Manager")
					? __("Switch it on in {0}.", [`<a href="/app/ph-modules">${__("Modules")}</a>`])
					: __("Ask your administrator to switch it on.")),
		});
	}

	function guard() {
		const what = M.blocked() || M.blocked_slug();
		if (!what) return;
		notice(what);
		frappe.set_route("");
	}

	// Stop before the page renders, so Frappe's own "Not found" never shows for a hidden doctype
	function patch_router() {
		if (!frappe.router || frappe.router.__ph_modules) return;
		const render = frappe.router.render;
		frappe.router.render = function () {
			const route = this.current_route || [];
			const what = M.blocked(route) || M.blocked_slug(route);
			if (what) {
				notice(what);
				this.current_route = [""];
				frappe.views.pageview && frappe.views.pageview.show("");
				setTimeout(() => frappe.set_route(""), 0);
				return;
			}
			return render.apply(this, arguments);
		};
		frappe.router.__ph_modules = true;
	}

	function patch_onboarding() {
		const Widget = frappe.widget && frappe.widget.widget_factory && frappe.widget.widget_factory.onboarding;
		if (!Widget || Widget.prototype.__ph_modules) return !!Widget;
		const original = Widget.prototype.make_body;
		Widget.prototype.make_body = function () {
			if (Array.isArray(this.steps) && (info().steps || []).length) {
				this.steps = this.steps.filter((s) => !has("steps", s.name));
			}
			return original.call(this);
		};
		Widget.prototype.__ph_modules = true;
		return true;
	}

	patch_router();
	$(document).on("app_ready", () => {
		patch_router();
		patch_onboarding();
		frappe.router.on("change", guard);
		guard();
	});
	patch_onboarding();
})();
