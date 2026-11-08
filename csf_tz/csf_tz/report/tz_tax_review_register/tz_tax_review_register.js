frappe.query_reports["TZ Tax Review Register"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1,
			default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1,
			default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1,
			default: frappe.datetime.get_today() },
		{ fieldname: "account", label: __("Account"), fieldtype: "Link", options: "Account",
			get_query: () => ({ filters: { company: frappe.query_report.get_filter_value("company"), is_group: 0 } }) },
		{ fieldname: "source_doctype", label: __("Voucher Type"), fieldtype: "Link", options: "DocType" },
		{ fieldname: "exceptions_only", label: __("Exceptions Only"), fieldtype: "Check", default: 1 },
		{ fieldname: "include_balance_sheet", label: __("Include Balance Sheet"), fieldtype: "Check" },
	],
	onload(report) {
		if (frappe.user.has_role("Accounts Manager") || frappe.user.has_role("System Manager")) {
			report.page.add_inner_button(__("Set Up Tax Categories and Sources"), () => frappe.call({
				method: "csf_tz.tax_computation.setup.setup_phase_one",
				callback: ({ message }) => { frappe.msgprint(message); report.refresh(); },
			}));
		}
		report.page.add_inner_button(__("Review Selected Ledger Entry"), () => {
			const dialog = new frappe.ui.Dialog({ title: __("Open Tax Review"),
				fields: [{ fieldname: "gl_entry", label: __("GL Entry"), fieldtype: "Link", options: "GL Entry", reqd: 1 }],
				primary_action_label: __("Open"),
				primary_action: ({ gl_entry }) => frappe.call({
					method: "csf_tz.tax_computation.service.new_review", args: { gl_entry },
					callback: ({ message }) => { dialog.hide(); const doc = frappe.model.sync(message)[0];
						frappe.set_route("Form", doc.doctype, doc.name); },
				}),
			});
			dialog.show();
		});
	},
};
