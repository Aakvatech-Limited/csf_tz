frappe.ui.form.on('Fees', {
    refresh: function (frm) {
        if (frm.doc.docstatus == 1 && frm.doc.outstanding_amount > 0) {
            frm.add_custom_button(__("Invoice Submission"), function () {
                frappe.call({
                    method: 'csf_tz.bank_api.invoice_submission',
                    args: {
                        fees_name: frm.doc.name,
                    },
                    callback: function (r) {
                        if (r.message) {
                            console.log(r.message);
                        }
                    }
                });
            });
        };
        frm.set_query("sales_invoice_income_account", function () {
            return {
                filters: [
                    ["Account", "company", "=", frm.doc.company]
                ]
            };
        });
    },
});
