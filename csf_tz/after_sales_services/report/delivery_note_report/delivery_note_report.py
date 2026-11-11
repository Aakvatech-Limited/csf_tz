# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder.functions import Concat


def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "delivery_note",
			"label": _("Delivery Note"),
			"fieldtype": "Link",
			"options": "Delivery Note",
			"width": 150		
		},
		{
			"fieldname": "customer_name",
			"label": _("Customer"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "customer_address",
			"label": _("Customer Address"),
			"fieldtype": "Small Text",
			"width": 200
		},
		{
			"fieldname": "phone_number",
			"label": _("Phone Number"),
			"fieldtype": "Data",
			"width": 150
		},
		# {
		# 	"fieldname": "item_name",
		# 	"label": _("Item"),
		# 	"fieldtype": "Data",
		# 	"width": 150		
		# },
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "quantity",
			"label": _("Quantity"),
			"fieldtype": "Float",
			"width": 150
		},
		# {
		# 	"fieldname": "uom",
		# 	"label": _("UOM"),
		# 	"fieldtype": "Data",
		# 	"width": 150
		# },
		{
			"fieldname": "serial_no",
			"label": _("Serial Numbers"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "actual_quantity",
			"label": _("Actual Quantity"),
			"fieldtype": "Float",
			"width": 100
		},
		# {
		# 	"fieldname": "projected_quantity",
		# 	"label": _("Projected Quantity"),
		# 	"fieldtype": "Float",
		# 	"width": 100
		# },
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "sales_invoice",
			"label": _("Sales Invoice"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150		
		}
	]
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	delivery_note_item = frappe.qb.DocType("Delivery Note Item")
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	delivery_note = frappe.qb.DocType("Delivery Note")
	stock_bin = frappe.qb.DocType("Bin")
	item = frappe.qb.DocType("Item")
	address = frappe.qb.DocType("Address")
	dynamic_link = frappe.qb.DocType("Dynamic Link")
	return_note = frappe.qb.DocType("Delivery Note").as_("return_note")

	customer_address_name = (
		frappe.qb.from_(dynamic_link)
		.select(dynamic_link.parent)
		.where(dynamic_link.parenttype == 'Address')
		.where(dynamic_link.link_doctype == 'Customer')
		.where(dynamic_link.link_name == delivery_note.customer)
		.orderby(address.creation)
		.limit(1)
	)
	return_against_note = (
		frappe.qb.from_(return_note)
		.select(return_note.name)
		.where(return_note.return_against == delivery_note.name)
	)

	query = (
		frappe.qb.from_(delivery_note_item)
		.left_join(sales_invoice)
		.on(delivery_note_item.against_sales_invoice == sales_invoice.name)
		.left_join(delivery_note)
		.on(delivery_note_item.parent == delivery_note.name)
		.left_join(stock_bin)
		.on((stock_bin.item_code == delivery_note_item.item_code) & (stock_bin.warehouse == delivery_note_item.warehouse))
		.left_join(item)
		.on(item.item_code == delivery_note_item.item_code)
		.left_join(address)
		.on(address.name == customer_address_name)
		.select(
			delivery_note.customer_name,
			Concat(address.address_line1, ",", address.city, ",", address.country).as_("customer_address"),
			address.phone.as_("phone_number"),
			delivery_note.posting_date,
			delivery_note_item.item_name,
			delivery_note_item.item_code,
			delivery_note_item.serial_no,
			delivery_note_item.qty.as_("quantity"),
			delivery_note_item.uom,
			delivery_note_item.warehouse,
			delivery_note.name.as_("delivery_note"),
			sales_invoice.name.as_("sales_invoice"),
			stock_bin.actual_qty.as_("actual_quantity"),
			stock_bin.projected_qty.as_("projected_quantity"),
		)
		.where(delivery_note.docstatus == 1)
		.where(delivery_note.status.isin(['Completed', 'To Bill', 'Closed']))
		.where(delivery_note.posting_date[filters.from_date:filters.to_date])
		.where(return_against_note.isnull())
	)

	if filters.warehouse:
		query = query.where(delivery_note_item.warehouse == filters.warehouse)

	data = query.run(as_dict=1)
	return columns, data
