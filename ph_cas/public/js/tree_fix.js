// B83 (LDG-230): Frappe 16.60's row menu runs "Add Child" on the selected node, not on the row
// whose menu was opened, so a new account could land under the wrong group. Each row action now
// selects its own row first.
(function () {
	function patch() {
		const TV = frappe.views && frappe.views.TreeView;
		if (!TV || TV.prototype.__ph_tree_fix) return !!TV;
		const original = TV.prototype.get_toolbar;
		TV.prototype.get_toolbar = function () {
			const me = this;
			return (original.apply(this, arguments) || []).map((btn) => {
				if (!btn || typeof btn.click !== "function" || btn.__ph_wrapped) return btn;
				const click = btn.click;
				return Object.assign({}, btn, {
					__ph_wrapped: true,
					click: function (node) {
						if (node && me.tree && me.tree.set_selected_node) me.tree.set_selected_node(node);
						return click.apply(this, arguments);
					},
				});
			});
		};
		TV.prototype.__ph_tree_fix = true;
		return true;
	}
	if (!patch()) $(document).on("app_ready", patch);
})();
