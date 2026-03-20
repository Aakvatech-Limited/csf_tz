frappe.ui.form.on("Salary Calculator", {
	refresh(frm) {
		setFieldState(frm);
	},

	results_add(frm) {
		triggerCalculation(frm);
	},

	results_remove(frm) {
		triggerCalculation(frm);
	},

	salary_structure(frm) {
		triggerCalculation(frm);
	},

	calculate_based_on(frm) {
		setFieldState(frm);
		triggerCalculation(frm);
	},

	net_pay(frm) {
		if (frm.doc.calculate_based_on === "Net Pay") {
			triggerCalculation(frm);
		}
	},

	gross_pay(frm) {
		if (frm.doc.calculate_based_on === "Gross Pay") {
			triggerCalculation(frm);
		}
	},

	allowance(frm) {
		triggerCalculation(frm);
	},
});

function setFieldState(frm) {
	const isNetPay = frm.doc.calculate_based_on === "Net Pay";
	const isGrossPay = frm.doc.calculate_based_on === "Gross Pay";

	frm.set_df_property("net_pay", "read_only", isGrossPay ? 1 : 0);
	frm.set_df_property("gross_pay", "read_only", isNetPay ? 1 : 0);
	frm.toggle_reqd("net_pay", isNetPay);
	frm.toggle_reqd("gross_pay", isGrossPay);
}

function triggerCalculation(frm) {
	if (frm.__applying_salary_calculation || !frm.doc.salary_structure || !frm.doc.calculate_based_on) {
		return;
	}

	const targetAmount =
		frm.doc.calculate_based_on === "Net Pay" ? frm.doc.net_pay : frm.doc.gross_pay;

	if (!targetAmount) {
		return;
	}

	frappe.call({
		method: "csf_tz.csf_tz.doctype.salary_calculator.salary_calculator.calculate_salary",
		args: {
			doc: frm.doc,
		},
		callback: async (r) => {
			if (!r.message) {
				return;
			}

			frm.__applying_salary_calculation = true;
			await frm.set_value({
				base: r.message.base,
				gross_pay: r.message.gross_pay,
				net_pay: r.message.net_pay,
				total_deductions: r.message.total_deductions,
				calculation_summary: r.message.calculation_summary,
			});

			frm.clear_table("results");
			for (const row of r.message.results || []) {
				const child = frm.add_child("results");
				child.salary_component = row.salary_component;
				child.amount = row.amount;
			}

			frm.refresh_field("results");
			frm.__applying_salary_calculation = false;
		},
	});
}

frappe.ui.form.on("Salary Calculator Result", {
	salary_component(frm) {
		triggerCalculation(frm);
	},
});
