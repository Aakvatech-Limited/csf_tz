# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder import Field
from frappe.query_builder.functions import Concat


def execute(filters=None):
	columns, data = [], []
	columns = [
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
		{
			"fieldname": "item_name",
			"label": _("Item"),
			"fieldtype": "Data",
			"width": 150		
		},
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
		{
			"fieldname": "uom",
			"label": _("UOM"),
			"fieldtype": "Data",
			"width": 150
		},
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
		{
			"fieldname": "projected_quantity",
			"label": _("Projected Quantity"),
			"fieldtype": "Float",
			"width": 100
		},
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
		},
		{
			"fieldname": "sales_order",
			"label": _("Sales Order"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 150		
		}
	]
	
	sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
	item = frappe.qb.DocType("Item")
	query = get_marked_items_query(sales_invoice_item, item)

	if filters.warehouse:
		query = query.where(sales_invoice_item.warehouse == filters.warehouse)
		
	if filters.item_group:
		query = query.where(item.item_group == filters.item_group)
	
	data = query.run(as_dict=True)
	return columns, data


def get_marked_items_query(sales_invoice_item, item):
	sales_order = frappe.qb.DocType("Sales Order")
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	stock_bin = frappe.qb.DocType("Bin")
	address = frappe.qb.DocType("Address")
	dynamic_link = frappe.qb.DocType("Dynamic Link")
	return_invoice = frappe.qb.DocType("Sales Invoice").as_("return_invoice")
	customer_address_name = (
		frappe.qb.from_(dynamic_link)
		.select(dynamic_link.parent)
		.where(dynamic_link.parenttype == 'Address')
		.where(dynamic_link.link_doctype == 'Customer')
		.where(dynamic_link.link_name == sales_invoice.customer)
		.orderby(address.creation)
		.limit(1)
	)
	first_return_invoice = (
		frappe.qb.from_(return_invoice)
		.select(return_invoice.name)
		.where(return_invoice.return_against == sales_invoice.name)
		.limit(1)
	)
	return (
		frappe.qb.from_(sales_invoice_item)
		.left_join(sales_order).on(sales_invoice_item.sales_order == sales_order.name)
		.left_join(sales_invoice).on(sales_invoice_item.parent == sales_invoice.name)
		.left_join(stock_bin).on((stock_bin.item_code == sales_invoice_item.item_code) & (stock_bin.warehouse == sales_invoice_item.warehouse))
		.left_join(item).on(item.item_code == sales_invoice_item.item_code)
		.left_join(address).on(address.name == customer_address_name)
		.select(
			sales_invoice.customer_name,
			Concat(address.address_line1, ",", address.city, ',', address.country).as_("customer_address"),
			address.phone.as_("phone_number"),
			sales_invoice_item.item_name,
			sales_invoice_item.item_code,
			sales_invoice_item.serial_no,
			sales_invoice_item.qty.as_("quantity"),
			sales_invoice_item.uom,
			sales_invoice_item.warehouse,
			sales_invoice.name.as_("sales_invoice"),
			sales_order.name.as_("sales_order"),
			stock_bin.actual_qty.as_("actual_quantity"),
			stock_bin.projected_qty.as_("projected_quantity"),
		)
		.where(Field("is_marked") == 1)
		.where(sales_invoice_item.delivered_qty < sales_invoice_item.qty)
		.where(sales_invoice.docstatus == 1)
		.where(sales_invoice.status.isin(['Submitted', 'Paid', 'Overdue', 'Unpaid']))
		.where(first_return_invoice.isnull())
	)
