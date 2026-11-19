// B72: Record an expense (after ECOUNT's payment journal). One dialog for a bill that is already
// paid; it posts a paid Purchase Invoice, so input VAT, EWT and the 2307 are worked out as usual.
frappe.provide("ph_cas");

ph_cas.record_expense = function (company) {
	const d = new frappe.ui.Dialog({
		title: __("Record an expense"),
		fields: [
			{ fieldname: "company", fieldtype: "Link", options: "Company", label: __("Company"), reqd: 1,
				default: company || frappe.defaults.get_user_default("Company") },
			{ fieldname: "supplier", fieldtype: "Link", options: "Supplier", label: __("Paid to"), reqd: 1 },
			{ fieldname: "description", fieldtype: "Data", label: __("What for"), reqd: 1 },
			{ fieldname: "item_code", fieldtype: "Link", options: "Item", label: __("Item (optional)"),
				get_query: () => ({ filters: { is_stock_item: 0, is_purchase_item: 1, disabled: 0 } }),
				description: __("Picks the expense account and VAT class from the item.") },
			{ fieldname: "expense_account", fieldtype: "Link", options: "Account", label: __("Expense account"), mandatory_depends_on: "eval:!doc.item_code",
				get_query: () => ({ filters: { company: d.get_value("company"), root_type: "Expense", is_group: 0 } }) },
			{ fieldname: "vat_class", fieldtype: "Select", label: __("VAT class"), options: "\nVATable\nVAT-exempt\nZero-rated" },
			{ fieldname: "col", fieldtype: "Column Break" },
			{ fieldname: "amount", fieldtype: "Currency", label: __("Amount on the receipt"), reqd: 1,
				description: __("Including VAT when the supplier is VAT-registered.") },
			{ fieldname: "receipt_no", fieldtype: "Data", label: __("Receipt or invoice no.") },
			{ fieldname: "receipt_date", fieldtype: "Date", label: __("Receipt date"), default: frappe.datetime.get_today() },
			{ fieldname: "paid_from", fieldtype: "Link", options: "Account", label: __("Paid from"),
				get_query: () => ({ query: "ph_cas.expense.paid_from_query", filters: { company: d.get_value("company") } }),
				description: __("Cash, a bank account, or the Company Credit Card.") },
			{ fieldname: "mode_of_payment", fieldtype: "Link", options: "Mode of Payment", label: __("Mode of payment") },
			{ fieldname: "sb", fieldtype: "Section Break" },
			{ fieldname: "figures", fieldtype: "HTML" },
		],
		primary_action_label: __("Post"),
		primary_action(v) {
			frappe.call({ method: "ph_cas.expense.record_expense", args: v, freeze: true }).then((r) => {
				d.hide();
				frappe.show_alert({ message: __("Posted {0}: paid {1}", [r.message.purchase_invoice, format_currency(r.message.paid)]), indicator: "green" });
				frappe.set_route("Form", "Purchase Invoice", r.message.purchase_invoice);
			});
		},
		secondary_action_label: __("Preview"),
		secondary_action() {
			const v = d.get_values();
			if (!v) return;
			frappe.call({ method: "ph_cas.expense.preview_expense", args: v }).then((r) => {
				const f = r.message;
				d.fields_dict.figures.$wrapper.html(`<table class="table table-condensed" style="margin:0">
					<tr><td>${__("Net of VAT")}</td><td class="text-right">${format_currency(f.net)}</td></tr>
					<tr><td>${__("Input VAT")}</td><td class="text-right">${format_currency(f.vat)}</td></tr>
					<tr><td>${__("Withheld (EWT)")} ${f.ewt_atc ? "(" + f.ewt_atc + ")" : ""}</td><td class="text-right">${format_currency(f.ewt)}</td></tr>
					<tr><th>${__("Cash paid")}</th><th class="text-right">${format_currency(f.paid)}</th></tr></table>
					${f.ewt ? `<p class="text-muted small">${__("The supplier is owed a 2307 for the tax withheld; it is made with the quarter's 2307s.")}</p>` : ""}`);
			});
		},
	});
	d.show();
};
