// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt
frappe.query_reports["Depreciation Transaction Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "periodicity",
			label: __("Periodicity"),
			fieldtype: "Select",
			options: [
				{ value: "Monthly", label: __("Monthly") },
				{ value: "Quarterly", label: __("Quarterly") },
				{ value: "Yearly", label: __("Yearly") }
			],
			default: "Monthly",
			reqd: 1,
			on_change: function() {
				let periodicity = frappe.query_report.get_filter_value('periodicity');
				let today = frappe.datetime.get_today();
				
				if(periodicity === "Quarterly") {
					// Get current quarter
					let quarter = Math.floor((frappe.datetime.str_to_obj(today).getMonth() + 3) / 3);
					let from_date;
					
					// Set date range based on current quarter
					switch(quarter) {
						case 1: // Jan-Mar
							from_date = frappe.datetime.year_start(today);
							break;
						case 2: // Apr-Jun
							from_date = frappe.datetime.add_months(frappe.datetime.year_start(today), 3);
							break;
						case 3: // Jul-Sep
							from_date = frappe.datetime.add_months(frappe.datetime.year_start(today), 6);
							break;
						case 4: // Oct-Dec
							from_date = frappe.datetime.add_months(frappe.datetime.year_start(today), 9);
							break;
					}
					
					let to_date = frappe.datetime.add_months(from_date, 3);
					to_date = frappe.datetime.add_days(to_date, -1);
					
					frappe.query_report.set_filter_value('from_date', from_date);
					frappe.query_report.set_filter_value('to_date', to_date);
				} 
				else if (periodicity === "Yearly") {
					let fiscal_year = frappe.defaults.get_user_default("fiscal_year");
					
					if (!fiscal_year) {
						// If no fiscal year is set, use calendar year
						let from_date = frappe.datetime.year_start(today);
						let to_date = frappe.datetime.year_end(today);
						
						frappe.query_report.set_filter_value('from_date', from_date);
						frappe.query_report.set_filter_value('to_date', to_date);
					} else {
						frappe.db.get_value("Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"], (r) => {
							if (r) {
								frappe.query_report.set_filter_value('from_date', r.year_start_date);
								frappe.query_report.set_filter_value('to_date', r.year_end_date);
							}
						});
					}
				}
				else {
					// Monthly - default to current month
					let from_date = frappe.datetime.month_start(today);
					let to_date = frappe.datetime.month_end(today);
					
					frappe.query_report.set_filter_value('from_date', from_date);
					frappe.query_report.set_filter_value('to_date', to_date);
				}
			}
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(frappe.datetime.get_today()),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(frappe.datetime.get_today()),
			reqd: 1,
		},
		{
			fieldname: "asset",
			label: __("Asset"),
			fieldtype: "Link",
			options: "Asset",
		},
		{
			fieldname: "asset_category",
			label: __("Asset Category"),
			fieldtype: "Link",
			options: "Asset Category",
		},
		{
			fieldname: "finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book",
		},
		// {
		// 	fieldname: "include_default_book_assets",
		// 	label: __("Include Default FB Assets"),
		// 	fieldtype: "Check",
		// 	default: 1,
		// },
	]
  };