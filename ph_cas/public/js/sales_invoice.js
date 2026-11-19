// LDG-96: an issued invoice, credit note or debit note (one with a BIR serial)
// is never cancelled; the server refuses it (ph_cas.invoicing.rules.refuse_cancel).
// This keeps the Cancel button out of sight and points to the correction path.
frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (frm.doc.docstatus !== 1 || !frm.doc.bir_serial) return;
        if (frm.perm && frm.perm[0]) frm.perm[0].cancel = 0;
        frm.page.clear_secondary_action();
        frm.dashboard.set_headline(
            __("Issued with BIR serial {0}. It cannot be cancelled: correct it with a credit note or a debit note.", [frm.doc.bir_serial])
        );
    },
});

// B75/B76 (after ECOUNT's simple input screens): the counter view of the Sales Invoice (ph_cas.counter_view in counter.js)
frappe.provide("ph_cas");
ph_cas.SI_COUNTER_FIELDS = new Set([
	"customer", "customer_name", "tax_id", "company", "posting_date", "due_date", "is_pos", "pos_profile", "is_return", "return_against",
	"update_stock", "set_warehouse", "scan_barcode", "items", "total_qty", "total", "net_total", "taxes", "total_taxes_and_charges",
	"discount_amount", "additional_discount_percentage", "grand_total", "rounding_adjustment", "rounded_total", "in_words", "outstanding_amount",
	"payments", "paid_amount", "change_amount", "remarks", "bir_serial",
]);
frappe.ui.form.on("Sales Invoice", {
	refresh(frm) { ph_cas.counter_view(frm, ph_cas.SI_COUNTER_FIELDS, "ph-si-counter-view"); },
});
