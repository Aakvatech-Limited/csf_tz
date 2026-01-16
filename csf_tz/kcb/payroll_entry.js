const kcbButtonName = "Generate KCB Payments Initiation";

frappe.ui.form.on("Payroll Entry", {
	refresh: function (frm) {
		frappe.db.get_single_value("KCB Settings", "enabled").then((enabled) => {
			if (!enabled) {
				frm.remove_custom_button(__(kcbButtonName));
				return;
			}
			if (frm.doc.docstatus === 1) {
				validate_salary_slips(frm);
			} else {
				frm.remove_custom_button(__(kcbButtonName));
			}
		});
	},
});

function validate_salary_slips(frm) {
	let all_submitted = true;
	frappe.db
		.get_list("Salary Slip", {
			fields: ["name", "docstatus"],
			filters: { payroll_entry: frm.doc.name },
		})
		.then((rows) => {
			if (!rows.length) {
				all_submitted = false;
			}
			rows.forEach((row) => {
				if (row.docstatus !== 1) {
					all_submitted = false;
				}
			});
			if (all_submitted) {
				add_kcb_payments_initiation_button(frm);
			} else {
				frm.remove_custom_button(__(kcbButtonName));
			}
		});
}

function add_kcb_payments_initiation_button(frm) {
	frm.add_custom_button(__(kcbButtonName), function () {
		frappe.call({
			method: "csf_tz.kcb.payments.make_kcb_payments_initiation_from_payroll_entry",
			args: { payroll_entry_name: frm.doc.name },
			callback: function (r) {
				if (r.message) {
					frappe.set_route("Form", "KCB Payments Initiation", r.message);
				}
			},
		});
	});
}
