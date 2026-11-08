// B02: the Company form's "Delete Transactions" action is removed. The server
// refuses the Transaction Deletion Record anyway; this keeps the button out of sight.
// B10: one-click Philippine setup.
frappe.ui.form.on("Company", {
    refresh(frm) {
        setTimeout(() => {
            frm.remove_custom_button(__("Delete Transactions"), __("Manage"));
            frm.remove_custom_button(__("Delete Transactions"));
        }, 0);
        if (!frm.is_new()) {
            frm.add_custom_button(__("Set up Philippine company"), () => {
                frappe.call({
                    method: "ph_cas.setup.chart.setup_philippine_company",
                    args: { company: frm.doc.name },
                    freeze: true,
                    callback(r) {
                        const m = r.message || {};
                        frappe.msgprint(__("Accounts added: {0}. Mappings added: {1}. BIR series added: {2}.", [
                            (m.accounts || []).length, (m.mapping || []).length, (m.series || []).length]));
                        frm.reload_doc();
                    },
                });
            }, __("PH CAS"));
            frm.add_custom_button(__("Registration pack (zip)"), () => {
                window.open(`/api/method/ph_cas.registration.pack.download_pack?company=${encodeURIComponent(frm.doc.name)}`);
            }, __("PH CAS"));
            frm.add_custom_button(__("Year-end e-books (zip)"), () => {
                frappe.prompt({ fieldname: "year", fieldtype: "Int", label: __("Year"), default: new Date().getFullYear() - 1, reqd: 1 }, (v) => {
                    window.open(`/api/method/ph_cas.books.yearend.download_pack?company=${encodeURIComponent(frm.doc.name)}&year=${v.year}`);
                }, __("Year-end e-books"));
            }, __("PH CAS"));
        }
    },
});
