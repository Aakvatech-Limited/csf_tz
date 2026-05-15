from __future__ import unicode_literals

import frappe


def update_module(report_name, module):
	doc = frappe.get_doc("Report", report_name)
	doc.module = module
	doc.save()


def execute():
	reports = [
		("Stock Ageing", "Stock"),
		("Stock Projected Qty", "Stock"),
		("Item Price Stock", "Stock"),
		("Item Shortage Report", "Stock"),
		("Items To Be Requested", "Stock"),
		("Itemwise Recommended Reorder Level", "Stock"),
		("Requested Items To Be Transferred", "Stock"),
		("Total Stock Summary", "Stock"),
	]

	for report_name, module in reports:
		update_module(report_name, module)
