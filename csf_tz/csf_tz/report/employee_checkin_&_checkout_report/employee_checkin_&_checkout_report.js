// Copyright (c) 2016, Aakvatech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Employee Checkin & Checkout Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "150px",
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "150px",
			"reqd": 1
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": "150px",
			"reqd": 1
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"default": "",
			"width": "150px",
			"reqd": 0,
			"get_query": function () {
				var company = frappe.query_report.get_filter_value("company");
				return {
					"doctype": "Department",
					"filters": {
						"company": company,
					}
				};
			}
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": "150px",
			"reqd": 0
		}
	],
	"onload": function(report) {
		frappe.call({
			method: "csf_tz.csf_tz.report.employee_checkin_&_checkout_report.employee_checkin_&_checkout_report.get_employee_checkin_summary",
			callback: function(r) {
				if (r.message) {
					// Remove any previous summary
					$('#employee-checkin-summary').remove();
					// Create two cards for IN and OUT
					let summary_html = `
						<div id="employee-checkin-summary" style="display: flex; gap: 16px; justify-content: center; margin-bottom: 16px;">
							<div class="card text-white bg-success mb-3" style="max-width: 18rem;">
								<div class="card-header">IN</div>
								<div class="card-body">
									<h5 class="card-title">${r.message.in_count}</h5>
									<p class="card-text">Checkins for <b>${r.message.date}</b></p>
								</div>
							</div>
							<div class="card text-white bg-danger mb-3" style="max-width: 18rem;">
								<div class="card-header">OUT</div>
								<div class="card-body">
									<h5 class="card-title">${r.message.out_count}</h5>
									<p class="card-text">Checkouts for <b>${r.message.date}</b></p>
								</div>
							</div>
						</div>
					`;

					// Insert above the filters
					$(summary_html).insertBefore('.page-form');
				}
			}
		});
	}
};