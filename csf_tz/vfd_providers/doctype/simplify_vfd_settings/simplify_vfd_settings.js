// Copyright (c) 2024, Aakvatech Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Simplify VFD Settings', {
	// refresh: function(frm) {

	// }
	get_token: (frm) => {
		frappe.call({
			method: "get_bearer_token",
			doc: frm.doc,
			args: {},
			freeze: true,
			freeze_message: __("Please Wait..."),
			callback: (r) => {
				if (r.message) {
					frm.refresh();
				}
			}
		})
	},
});
