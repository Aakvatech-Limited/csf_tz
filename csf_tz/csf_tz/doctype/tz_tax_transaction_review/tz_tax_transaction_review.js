frappe.ui.form.on("TZ Tax Transaction Review", {
	refresh(frm) {
		frm.set_query("gl_entry", () => ({ filters: { is_cancelled: 0 } }));
		frm.set_query("tax_category", "allocations", () => ({ filters: { disabled: 0 } }));
	},
	gl_entry(frm) {
		if (!frm.is_new() || !frm.doc.gl_entry) return;
		frappe.call({
			method: "csf_tz.tax_computation.service.new_review",
			args: { gl_entry: frm.doc.gl_entry },
			callback: ({ message }) => {
				if (!message.__islocal) {
					frappe.set_route("Form", message.doctype, message.name);
					return;
				}
				["company", "posting_date", "source_doctype", "source_name", "account", "source_detail",
					"net_amount", "currency", "allocations"].forEach((key) => frm.set_value(key, message[key]));
			},
		});
	},
});
