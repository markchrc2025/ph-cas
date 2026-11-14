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
