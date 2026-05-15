from __future__ import unicode_literals

import frappe


def execute():
	stock_entry_type_list = [
		{"name": "To Company", "purpose": "Material Receipt"},
		{"name": "From Company", "purpose": "Material Issue"},
	]

	for stock_entry_type_data in stock_entry_type_list:
		stock_entry_doc = frappe.new_doc("Stock Entry Type")
		stock_entry_doc.name = stock_entry_type_data["name"]
		stock_entry_doc.purpose = stock_entry_type_data["purpose"]
		stock_entry_doc.insert(ignore_permissions=True)
		stock_entry_doc.save()
