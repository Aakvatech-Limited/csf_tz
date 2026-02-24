// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Cycle Report"] = {
	"filters": [
		{
				"fieldname": "from_date",
				"label": __("From Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.month_start(),
				"reqd": 1
		},
		{
				"fieldname": "to_date",
				"label": __("To Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.get_today(),
				"reqd": 1
		},
		{
				"fieldname": "item_type",
				"label": __("Item Type"),
				"fieldtype": "Select",
				"options": "\nStock\nNon-Stock/Service",
				"default": ""
		},
		{
				"fieldname": "warehouse",
				"label": __("Warehouse"),
				"fieldtype": "Link",
				"options": "Warehouse"
		}
	]
};
