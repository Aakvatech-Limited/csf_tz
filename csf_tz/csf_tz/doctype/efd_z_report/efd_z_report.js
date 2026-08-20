frappe.ui.form.on('EFD Z Report Invoice', {
	include: (frm) => {
		let sum_excluding_vat_ticked = 0
		let sum_vat_ticked = 0
		let sum_turnover_exempted_sp_relief_ticked = 0
		let sum_turnover_ticked = 0
		frm.doc.efd_z_report_invoices.forEach(d => {
			if (d.include){
				sum_excluding_vat_ticked += d.amt_excl_vat;
			sum_vat_ticked += d.vat;
			sum_turnover_exempted_sp_relief_ticked += d.amt_ex__sr;
			sum_turnover_ticked += d.invoice_amount;
			}
		});
		frm.set_value("total_excluding_vat_ticked", sum_excluding_vat_ticked - sum_turnover_exempted_sp_relief_ticked);
		frm.set_value("total_vat_ticked", sum_vat_ticked);
		frm.set_value("total_turnover_exempted__sp_relief_ticked", sum_turnover_exempted_sp_relief_ticked);
		frm.set_value("total_turnover_ticked", sum_turnover_ticked);

	}
})


frappe.ui.form.on('EFD Z Report', {
	get_invoices: (frm) => {
		frm.clear_table("efd_z_report_invoices");
		frappe.call({
			method: "get_sales_invoice",
			doc: frm.doc,
			args: {
				"electronic_fiscal_device": frm.doc.electronic_fiscal_device,
				"date_and_time": frm.doc.z_report_date_time,
			},
			freeze: true,
			freeze_message: __("Fetching Invoices..."),
			callback: function (r) {
				frm.refresh_field("efd_z_report_invoices");
			}
		});
	},
	net_amount: (frm) => {
		calculate_total_turnover(frm);
	},
	total_vat: (frm) => {
		calculate_total_turnover(frm);
	},
	total_turnover_ex_sr: (frm) => {
		calculate_total_turnover(frm);
	},
})

const calculate_total_turnover = (frm) => {
	frm.doc.total_turnover = frm.doc.net_amount + frm.doc.total_vat +frm.doc.total_turnover_ex_sr;
	refresh_field("total_turnover");
}
