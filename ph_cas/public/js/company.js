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
            frm.add_custom_button(__("Quarterly notice of minor enhancements"), () => {
                const now = new Date();
                const q = Math.floor(now.getMonth() / 3) || 4;
                frappe.prompt([
                    { fieldname: "year", fieldtype: "Int", label: __("Year"), default: q === 4 && now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear(), reqd: 1 },
                    { fieldname: "quarter", fieldtype: "Select", label: __("Quarter"), options: "1\n2\n3\n4", default: String(q), reqd: 1 },
                ], (v) => {
                    window.open(`/api/method/ph_cas.ops.releases.download_quarterly_notice?company=${encodeURIComponent(frm.doc.name)}&year=${v.year}&quarter=${v.quarter}`);
                }, __("Notice of minor enhancements (RMO 9-2021 V.9)"));
            }, __("PH CAS"));
            frm.add_custom_button(__("Year-end e-books (zip)"), () => {
                frappe.prompt({ fieldname: "year", fieldtype: "Int", label: __("Year"), default: new Date().getFullYear() - 1, reqd: 1 }, (v) => {
                    window.open(`/api/method/ph_cas.books.yearend.download_pack?company=${encodeURIComponent(frm.doc.name)}&year=${v.year}`);
                }, __("Year-end e-books"));
            }, __("PH CAS"));
        }
    },
});
