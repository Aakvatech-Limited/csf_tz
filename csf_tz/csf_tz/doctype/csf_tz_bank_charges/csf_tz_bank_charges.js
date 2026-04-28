// Copyright (c) 2024, Aakvatech and contributors
// For license information, please see license.txt

frappe.ui.form.on("CSF TZ Bank Charges", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(
				__("Fetch Bank Charges from Transactions"),
				() => show_date_prompt(frm),
				__("Actions")
			);
		}
	},
});

const show_date_prompt = (frm) => {
	if (!frm.doc.bank_account) {
		frappe.msgprint(__("Please set Bank Account before fetching charges."));
		return;
	}

	if (!frm.doc.posting_date) {
		frappe.msgprint(__("Please set Posting Date before fetching charges."));
		return;
	}

	const posting_date = frappe.datetime.str_to_obj(frm.doc.posting_date);
	const default_from_date = frappe.datetime.obj_to_str(
		new Date(posting_date.getFullYear(), posting_date.getMonth(), 1)
	);
	const to_date = frm.doc.posting_date;

	frappe.prompt(
		[
			{
				label: __("From Date"),
				fieldname: "from_date",
				fieldtype: "Date",
				reqd: 1,
				default: default_from_date,
			},
			{
				label: __("To Date"),
				fieldname: "to_date",
				fieldtype: "Date",
				read_only: 1,
				default: to_date,
			},
		],
		(values) => {
			if (frappe.datetime.str_to_obj(values.from_date) > frappe.datetime.str_to_obj(to_date)) {
				frappe.msgprint(
					__("From Date cannot be after Posting Date ({0}).", [to_date])
				);
				return;
			}
			fetch_and_populate(frm, values.from_date, to_date);
		},
		__("Select Date Range"),
		__("Fetch Charges")
	);
};

const fetch_and_populate = (frm, from_date, to_date) => {
	frappe.call({
		method: "csf_tz.csf_tz.doctype.csf_tz_bank_charges.csf_tz_bank_charges.get_matched_bank_transactions",
		args: {
			bank_account: frm.doc.bank_account,
			from_date: from_date,
			to_date: to_date,
		},
		freeze: true,
		freeze_message: __("Fetching matching bank charges..."),
		callback(r) {
			const matched = r.message || [];

			if (!matched.length) {
				frappe.msgprint(
					__(
						"No matching bank charge transactions found for {0} between {1} and {2}.",
						[frm.doc.bank_account, from_date, to_date]
					)
				);
				return;
			}

			frappe.confirm(
				__(
					"This will clear the existing charges table and import {0} row(s) from {1} to {2}. Continue?",
					[matched.length, from_date, to_date]
				),
				() => {
					frm.clear_table("csf_tz_bank_charges_detail");

					matched.forEach((row) => {
						const child = frm.add_child("csf_tz_bank_charges_detail");
						child.value_date = row.date;
						child.description = row.description;
						child.debit_amount = flt(row.withdrawal);
						child.reference_number = row.reference_number || "";
						child.control_number = "";
					});

					frm.refresh_field("csf_tz_bank_charges_detail");

					frappe.show_alert(
						{
							message: __(
								"{0} charge(s) imported from {1} to {2}.",
								[matched.length, from_date, to_date]
							),
							indicator: "green",
						},
						5
					);
				}
			);
		},
	});
};
