// Copyright (c) 2026, Aakvatech and contributors
// For license information, please see license.txt

frappe.query_reports["PAYE Report Mapping"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.month_start()
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.month_end()
		}
	]
};
