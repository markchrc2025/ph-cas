// B02: the Company form's "Delete Transactions" action is removed. The server
// refuses the Transaction Deletion Record anyway; this keeps the button out of sight.
frappe.ui.form.on("Company", {
    refresh(frm) {
        setTimeout(() => {
            frm.remove_custom_button(__("Delete Transactions"), __("Manage"));
            frm.remove_custom_button(__("Delete Transactions"));
        }, 0);
    },
});
