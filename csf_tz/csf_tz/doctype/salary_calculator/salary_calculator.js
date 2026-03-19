frappe.ui.form.on("Salary Calculator", {
	refresh(frm) {
		setFieldState(frm);
	},

	employee(frm) {
		triggerCalculation(frm);
	},

	company(frm) {
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

	nssf(frm) {
		triggerCalculation(frm);
	},

	wcf(frm) {
		triggerCalculation(frm);
	},

	sdl(frm) {
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
	if (frm.__applying_salary_calculation) {
		return;
	}

	if (!frm.doc.employee || !frm.doc.calculate_based_on) {
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
			employee: frm.doc.employee,
			company: frm.doc.company,
			calculate_based_on: frm.doc.calculate_based_on,
			net_pay: frm.doc.net_pay,
			gross_pay: frm.doc.gross_pay,
			nssf: frm.doc.nssf,
			wcf: frm.doc.wcf,
			sdl: frm.doc.sdl,
		},
		callback: async (r) => {
			if (!r.message) {
				return;
			}

			frm.__applying_salary_calculation = true;
			await frm.set_value({
				company: r.message.company,
				salary_structure: r.message.salary_structure,
				base: r.message.base,
				net_pay: r.message.net_pay,
				gross_pay: r.message.gross_pay,
				nssf_amount: r.message.nssf_amount,
				wcf_amount: r.message.wcf_amount,
				sdl_amount: r.message.sdl_amount,
			});
			frm.__applying_salary_calculation = false;
		},
	});
}

