# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from csf_tz.sales_and_marketing.customer_address import get_customer_address


def execute(filters=None):
	columns, data = [], []
	columns = [
		{"fieldname": "date_of_sale", "label": _("Date of Sale"), "fieldtype": "Date", "width": 150},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
		{
			"fieldname": "customer_address",
			"label": _("Customer Address"),
			"fieldtype": "Small Text",
			"width": 200,
		},
		{"fieldname": "contact", "label": _("Customer Contacts"), "fieldtype": "Small Text", "width": 150},
		{"fieldname": "itm", "label": _("Item Sold"), "fieldtype": "Link", "options": "Item", "width": 200},
		{"fieldname": "brand", "label": _("Brand"), "fieldtype": "Link", "options": "Brand", "width": 150},
		{
			"fieldname": "name",
			"label": _("Serial No"),
			"fieldtype": "Link",
			"options": "Past Serial No",
			"width": 200,
		},
		{"fieldname": "amount", "label": _("Price"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "past_item_group", "label": _("Item Group"), "fieldtype": "Data", "width": 150},
	]

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	past_serial_no = frappe.qb.DocType("Past Serial No")
	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(past_serial_no)
		.left_join(item)
		.on(item.name == past_serial_no.item_code)
		.select(
			past_serial_no.customer,
			past_serial_no.name,
			past_serial_no.date_of_sale,
			past_serial_no.amount,
			past_serial_no.past_item_group,
			past_serial_no.item_code.as_("itm"),
			past_serial_no.past_item_group,
			item.brand,
		)
		.where(past_serial_no.docstatus == 1)
		.where(past_serial_no.date_of_sale[filters.from_date : filters.to_date])
		.groupby(past_serial_no.name)
		.orderby(past_serial_no.date_of_sale)
	)

	if filters.customer:
		query = query.where(past_serial_no.customer == filters.customer)

	if filters.brand:
		query = query.where(item.brand == filters.brand)

	data = query.run(as_dict=True)
	for customer in data:
		address = get_customer_address(customer.customer)
		if address:
			customer.update(address)

	return columns, data
