// Copyright (c) 2016, Aakvatech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Withholding Tax Payment Summary"] = {
	"filters": [
		{
			"fieldname": "rental",
			"label": __("Rental"),
			"fieldtype": "Select",
			"options": "Commercial Rent\nResidential Rent",
			"default": "Commercial Rent"
		}
	]
};
