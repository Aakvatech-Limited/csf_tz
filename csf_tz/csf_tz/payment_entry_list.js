frappe.listview_settings["Payment Entry"] = {
	add_fields: ["payment_type", "docstatus"],
	onload(listview) {
		frappe.db.get_single_value("KCB Settings", "enabled").then((enabled) => {
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
					frappe.call({
						method: "csf_tz.kcb.payments.make_kcb_payments_initiation_from_payment_entries",
						args: { payment_entries: eligible.map((row) => row.name) },
						callback: function (r) {
							if (r.message) {
								frappe.set_route("Form", "KCB Payments Initiation", r.message);
							}
						},
					});
				}
			);
		});
	},
};
