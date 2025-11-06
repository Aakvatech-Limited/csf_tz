frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Multi_Account Balance Timeline"] = {
	method: "csf_tz.csf_tz.dashboard_chart_source.multi_account_balance_timeline.multi_account_balance_timeline.get",
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
			fieldname: "account_type",
			label: __("Account Type"),
			fieldtype: "Select",
			options: "Bank\nCash",
			default: "Bank",
		},
		{
			fieldname: "currency",
			label: __("Currency"),
			fieldtype: "Link",
			options: "Currency",
		},
		{
			fieldname: "include_inactive",
			label: __("Include Inactive Accounts"),
			fieldtype: "Check",
			default: 0,
		}
	],
};
