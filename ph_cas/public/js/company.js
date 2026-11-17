// B02: the Company form's "Delete Transactions" action is removed. The server
// refuses the Transaction Deletion Record anyway; this keeps the button out of sight.
// B10: one-click Philippine setup.
// D9 (17 Nov 2026): the Company menu carries the product name, not the code name.
function ph_cas_menu() {
    return (frappe.boot.sysdefaults && frappe.boot.sysdefaults.app_name) || "Sentire Ledger";
}

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
            }, ph_cas_menu());
            frm.add_custom_button(__("Registration pack (zip)"), () => {
                window.open(`/api/method/ph_cas.registration.pack.download_pack?company=${encodeURIComponent(frm.doc.name)}`);
            }, ph_cas_menu());
            frm.add_custom_button(__("Loose-leaf books (Excel / PDF)"), () => {
                const y = new Date().getFullYear();
                frappe.prompt([
                    { fieldname: "from_date", fieldtype: "Date", label: __("From"), default: `${y}-01-01`, reqd: 1 },
                    { fieldname: "to_date", fieldtype: "Date", label: __("To"), default: frappe.datetime.get_today(), reqd: 1 },
                    { fieldname: "fmt", fieldtype: "Select", label: __("Format"), options: "pdf\nxlsx", default: "pdf", reqd: 1,
                      description: __("Six books, the header and page numbers on every page, and PAGES.txt with the page count of each book for the sworn statement.") },
                ], (v) => {
                    window.open(`/api/method/ph_cas.books.looseleaf.download?company=${encodeURIComponent(frm.doc.name)}&from_date=${v.from_date}&to_date=${v.to_date}&fmt=${v.fmt}`);
                }, __("Loose-leaf books of accounts"));
            }, ph_cas_menu());
            frm.add_custom_button(__("Quarterly notice of minor enhancements"), () => {
                const now = new Date();
                const q = Math.floor(now.getMonth() / 3) || 4;
                frappe.prompt([
                    { fieldname: "year", fieldtype: "Int", label: __("Year"), default: q === 4 && now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear(), reqd: 1 },
                    { fieldname: "quarter", fieldtype: "Select", label: __("Quarter"), options: "1\n2\n3\n4", default: String(q), reqd: 1 },
                ], (v) => {
                    window.open(`/api/method/ph_cas.ops.releases.download_quarterly_notice?company=${encodeURIComponent(frm.doc.name)}&year=${v.year}&quarter=${v.quarter}`);
                }, __("Notice of minor enhancements (RMO 9-2021 V.9)"));
            }, ph_cas_menu());
            if (!frm.doc.enable_perpetual_inventory) {
                // B69: periodic method; the year-end count becomes the inventory adjustment
                frm.add_custom_button(__("Year-end inventory adjustment"), () => {
                    frappe.prompt({ fieldname: "as_of", fieldtype: "Date", label: __("Count date"), default: frappe.datetime.get_today(), reqd: 1,
                        description: __("Enter the year-end count first (Stock Reconciliation on the count day).") }, (v) => {
                        frappe.call({ method: "ph_cas.stock.periodic.preview", args: { company: frm.doc.name, as_of: v.as_of } }).then((r) => {
                            const p = r.message;
                            frappe.confirm(__("Counted stock {0}, inventory in the books {1}: post {2} to cost of sales?", [
                                format_currency(p.counted), format_currency(p.books), format_currency(p.adjustment)]), () => {
                                frappe.call({ method: "ph_cas.stock.periodic.post_adjustment", args: { company: frm.doc.name, as_of: v.as_of }, freeze: true })
                                    .then((x) => frappe.msgprint(x.message.journal_entry ? __("Posted {0}.", [x.message.journal_entry]) : __("Nothing to adjust.")));
                            });
                        });
                    }, __("Year-end inventory adjustment"));
                }, ph_cas_menu());
            }
            frm.add_custom_button(__("Year-end e-books (zip)"), () => {
                frappe.prompt({ fieldname: "year", fieldtype: "Int", label: __("Year"), default: new Date().getFullYear() - 1, reqd: 1 }, (v) => {
                    window.open(`/api/method/ph_cas.books.yearend.download_pack?company=${encodeURIComponent(frm.doc.name)}&year=${v.year}`);
                }, __("Year-end e-books"));
            }, ph_cas_menu());
        }
    },
});
