# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	if not filters: filters = {}
	columns = get_columns()
	item_list = get_items(filters)

	data = []
	for d in item_list:
		row = [d.posting_date, d.itm,d.item_name, d.customer, d.warehouse,
			d.quantity, d.amount, d.brand, d.name]
		data.append(row)

	return columns, data


def get_columns():
	columns = [
		_("Due Date") + ":Date:80",
		_("Item Code") + ":Link/Item:120",
		_("Item Name") + ":Data:120",
		_("Customer") + ":Link/Customer:120",
		_("Warehouse") + ":Link/Warehouse:120",
		_("Qty") + ":Float:120",	
		_("Amount") + ":Float:120",
		_("Brand") + ":Link/Brand:120",
		_("Invoice") + ":Link/Sales Invoice:120",]

	return columns

def get_items(filters):
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	item = frappe.qb.DocType("Item")
	order_by = sales_invoice.posting_date

	if filters.brand:
		order_by &= (item.brand == filters.brand)

	if filters.shop:
		order_by &= (sales_invoice_item.warehouse == filters.shop)
	
	return (
		frappe.qb.from_(sales_invoice_item)
		.left_join(sales_invoice).on(sales_invoice.name == sales_invoice_item.parent)
		.left_join(item).on(item.item_code == sales_invoice_item.item_code)
		.select(
			sales_invoice.customer,
			sales_invoice.name,
			sales_invoice.posting_date,
			sales_invoice.grand_total,
			sales_invoice_item.warehouse,
			sales_invoice_item.item_code.as_("itm"),
			sales_invoice_item.item_name,
			sales_invoice_item.qty.as_("quantity"),
			sales_invoice_item.amount,
			item.brand.as_("brand"),
			sales_invoice_item.parent.as_("si_name"),
			sales_invoice.customer.as_("cust"),
		)
		.where(sales_invoice.docstatus == 1)
		.where(item.item_group == 'Spare Parts')
		.where(sales_invoice.customer == 'Guest')
		.where(sales_invoice.posting_date[filters.from_date:filters.to_date])
		.orderby(order_by)
		.run(as_dict=True)
	)
