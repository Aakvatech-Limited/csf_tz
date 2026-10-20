// Copyright (c) 2026, Aakvatech and contributors
// For license information, please see license.txt

frappe.query_reports["Item Price by Price List"] = {
	filters: [
		{
			fieldname: "item_description",
			label: __("Item or Part of Description"),
			fieldtype: "Data",
		},
		{
			fieldname: "barcode",
			label: __("Scan Barcode"),
			fieldtype: "Data",
		},
		{
			fieldname: "price_list",
			label: __("Price List"),
			fieldtype: "Link",
			options: "Price List",
			get_query: () => ({
				filters: {
					selling: 1,
				},
			}),
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "tax_rate",
			label: __("Tax Rate"),
			fieldtype: "Percent",
			default: 18,
			reqd: 1,
		},
		{
			fieldname: "only_with_stock",
			label: __("Only Items with Stock"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "only_with_price",
			label: __("Only Items with Price"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
