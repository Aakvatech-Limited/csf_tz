frappe.listview_settings["Payment Entry"] = {
	add_fields: ["payment_type", "docstatus"],
	onload(listview) {
		frappe.call({
			method: "csf_tz.kcb.api.kcb_api.is_kcb_enabled",
			callback: (r) => {
			const enabled = !!r.message;
			if (!enabled) {
				return;
			}
			listview.page.add_actions_menu_item(
				__("Generate KCB Payments Initiation"),
				function () {
					const selected = listview.get_checked_items();
					if (!selected.length) {
						frappe.msgprint(__("Please select at least one Payment Entry."));
						return;
					}
					const eligible = selected.filter(
						(row) => row.docstatus === 1 && row.payment_type === "Pay"
					);
					if (!eligible.length) {
						frappe.msgprint(__("Select submitted Pay type Payment Entries only."));
						return;
					}
					frappe.prompt(
						[
							{
								fieldname: "file_reference",
								fieldtype: "Data",
								label: __("File Name"),
								description: __(
									'Optional. e.g. "TRA MONTHLY SALARY AUGUST 2026". Leave blank to use the system-generated name.'
								),
							},
						],
						(values) => {
							frappe.call({
								method: "csf_tz.kcb.payments.make_kcb_payments_initiation_from_payment_entries",
								args: {
									payment_entries: eligible.map((row) => row.name),
									file_reference: values.file_reference,
								},
								callback: function (r) {
									if (r.message) {
										frappe.set_route("Form", "KCB Payments Initiation", r.message);
									}
								},
							});
						},
						__("Generate KCB Payments Initiation"),
						__("Generate")
					);
				}
			);
			},
		});
	},
};
