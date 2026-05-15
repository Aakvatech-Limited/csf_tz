// Copyright (c) 2016, Aakvatech and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.ui.form.on("Supplier", {


	refresh: function(frm) {

		if(!frm.doc.__islocal) {
			// custom buttons
			frm.add_custom_button(__('Multi-Currency Ledger'), function() {
				frappe.set_route('query-report', 'Multi-Currency Ledger',
					{party_type:'Supplier', party:frm.doc.name});
			});

		}
	},

});
