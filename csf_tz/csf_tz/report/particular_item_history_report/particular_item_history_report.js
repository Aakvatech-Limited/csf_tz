// Copyright (c) 2026, Aakvatech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Particular Item History Report"] = {
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
			"fieldname": "price_list",
			"label": __("Price List"),
			"fieldtype": "Link",
			"options": "Price List",
			"default": frappe.defaults.get_default("selling_price_list"),
			"reqd": 1,
			"get_query": () => {
				return {
					filters: {
						"selling": 1,
						"enabled": 1
					}
				};
			}
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		}
	]
};
