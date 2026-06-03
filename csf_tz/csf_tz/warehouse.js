frappe.ui.form.on("Warehouse", {

	refresh: function(frm, dt, dn) {

        frm.add_custom_button(__('Create Stock Reconciliation'),
            function() {
                frappe.call({
                    method: 'csf_tz.custom_api.make_stock_reconciliation_for_all_pending_material_request',
                });
            });

	},

});
