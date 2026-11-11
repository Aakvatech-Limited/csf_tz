# Copyright (c) 2024, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)

	data = get_data(filters)
	
	if len(data) == 0:
		frappe.msgprint("<strong>No record found, Please check you filters</strong>")
		return
	
	return columns, data

def get_data(filters):
	price_change_request = frappe.qb.DocType("Price Change Request")
	price_change_detail = frappe.qb.DocType("Price Change Request Detail")
	query = (
		frappe.qb.from_(price_change_request)
		.inner_join(price_change_detail)
		.on(price_change_request.name == price_change_detail.parent)
		.select(
			price_change_request.posting_date.as_("date"),
			price_change_detail.item_code,
			price_change_detail.item_name,
			price_change_detail.price_list,
			price_change_detail.old_price,
			price_change_detail.new_price,
		)
		.where(price_change_request.docstatus == 1)
		.where(price_change_request.company == filters.company)
	)

	if filters.item:
		query = query.where(price_change_detail.item_code == filters.item)

	if filters.price_list:
		query = query.where(price_change_detail.price_list == filters.price_list)

	if filters.from_date:
		query = query.where(price_change_request.posting_date >= filters.from_date)

	if filters.to_date:
		query = query.where(price_change_request.posting_date <= filters.to_date)

	return query.run(as_dict=True)

def get_columns(filters):
	return [
		{"fieldname": "date", "fieldtype": "Date", "label": _("Date"), "width": "110px"},
		{"fieldname": "item_code", "fieldtype": "Link", "options": "Item", "label": _("Item Code"), "width": "170px"},
		{"fieldname": "item_name", "fieldtype": "Data", "label": _("Item Name"), "width": "200px"},
		{"fieldname": "price_list", "fieldtype": "Link", "options": "Price List", "label": _("Price List"), "width": "170px"},
		{"fieldname": "old_price", "fieldtype": "Currency", "label": _("Old Price"), "width": "100px"},
		{"fieldname": "new_price", "fieldtype": "Currency", "label": _("New Price"), "width": "100px"}
	]