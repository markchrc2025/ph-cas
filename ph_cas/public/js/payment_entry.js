// B76: the counter view of the Payment Entry: a Cashier recording a collection sees the customer,
// the amount, where it went, the invoices it pays and the reference (ph_cas.counter_view, counter.js).
frappe.provide("ph_cas");
ph_cas.PE_COUNTER_FIELDS = new Set([
	"payment_type", "company", "posting_date", "mode_of_payment", "party_type", "party", "party_name", "paid_from", "paid_to",
	"paid_amount", "received_amount", "references", "get_outstanding_invoices", "total_allocated_amount", "unallocated_amount",
	"reference_no", "reference_date", "remarks", "deductions", "bir_serial",
]);
frappe.ui.form.on("Payment Entry", {
	refresh(frm) { ph_cas.counter_view(frm, ph_cas.PE_COUNTER_FIELDS, "ph-pe-counter-view"); },
});
