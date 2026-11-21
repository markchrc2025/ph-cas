// B84: an issued invoice may be cancelled (approval chains may gate it). The form says what
// cancelling means for its BIR serial.
frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.bir_serial) {
            frm.dashboard.set_headline(
                __("Issued with BIR serial {0}. Cancelling keeps the serial in the series as cancelled; a replacement takes the next serial.", [frm.doc.bir_serial])
            );
        }
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
