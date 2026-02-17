// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.ui.form.on("KCB Payments Initiation", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Check KCB Status"), () => {
				if (frm._kcb_status_inflight) {
					return;
				}
				frm._kcb_status_inflight = true;
				frappe.dom.freeze(__("Checking KCB status..."));
				frappe.call({
					method: "csf_tz.kcb.api.kcb_api.check_file_status",
					args: { docname: frm.doc.name },
					callback: (r) => {
						if (r.message) {
							const pretty = JSON.stringify(r.message, null, 2);
							frappe.msgprint({
								title: __("KCB Status"),
								message: `<pre>${frappe.utils.escape_html(pretty)}</pre>`,
							});
						}
					},
					always: () => {
						frm._kcb_status_inflight = false;
						frappe.dom.unfreeze();
					},
				});
			});
		}
	},
});
