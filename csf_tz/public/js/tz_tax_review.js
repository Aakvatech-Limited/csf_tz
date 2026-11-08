// Tax data lives in separate extension records; no custom source fields.
(() => {
	if (frappe._tz_tax_review_registered) return;
	frappe._tz_tax_review_registered = true;
	const open_review = (gl_entry) => frappe.call({
		method: "csf_tz.tax_computation.service.new_review",
		args: { gl_entry },
		callback: ({ message }) => {
			const doc = frappe.model.sync(message)[0];
			frappe.set_route("Form", doc.doctype, doc.name);
		},
	});
	["Purchase Invoice", "Sales Invoice", "Journal Entry", "Payment Entry", "GL Entry"].forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				if (frm.is_new() || (doctype !== "GL Entry" && frm.doc.docstatus !== 1)) return;
				if (!frappe.model.can_read("TZ Tax Transaction Review")) return;
				frm.add_custom_button(__("Income Tax Review"), () => {
					if (doctype === "GL Entry") return open_review(frm.doc.name);
					frappe.call({
						method: "csf_tz.tax_computation.service.source_entries",
						args: { source_doctype: doctype, source_name: frm.doc.name },
						callback: ({ message: entries }) => {
							if (!entries?.length) return frappe.msgprint(__("No eligible ledger entries found."));
							const dialog = new frappe.ui.Dialog({
								title: __("Select a Ledger Entry to Review"),
								fields: [{ fieldname: "gl_entry", fieldtype: "Select", label: __("Ledger Entry"),
									reqd: 1, options: entries.map((row) => ({ value: row.name,
										label: `${row.account} | ${row.debit - row.credit} | ${row.name}` })) }],
								primary_action_label: __("Open Tax Review"),
								primary_action: ({ gl_entry }) => { dialog.hide(); open_review(gl_entry); },
							});
							dialog.show();
						},
					});
				}, __("Tax"));
			},
		});
	});
})();
