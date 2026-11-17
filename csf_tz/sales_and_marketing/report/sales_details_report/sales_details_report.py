# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "posting_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
		{
			"fieldname": "customer_group",
			"label": _("Customer Group"),
			"fieldtype": "Link",
			"options": "Customer Group",
			"width": 150
		},
		{
			"fieldname": "item_no",
			"label": _("Item Sold"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 150
		},
		{
			"fieldname": "name",
			"label": _("Sales Invoice"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150		
		},
			{
			"fieldname": "grand_total",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "quantity",
			"label": _("Quantity"),
			"fieldtype": "data",
			"width": 150
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Data",
			"width": 150
		},
	]

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	sales_invoice = frappe.qb.DocType("Sales Invoice")
	sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
	customer = frappe.qb.DocType("Customer")
	group_by = sales_invoice.name

	if filters.customer:
		group_by &= (sales_invoice.customer == filters.customer)
	
	if filters.warehouse:
		group_by &= (sales_invoice_item.warehouse == filters.warehouse)

	if filters.cust_group:
		group_by &= (customer.customer_group == filters.cust_group)
	
	data = (
		frappe.qb.from_(sales_invoice)
		.left_join(sales_invoice_item).on(sales_invoice.name == sales_invoice_item.parent)
		.left_join(customer).on(customer.customer_name == sales_invoice.customer)
		.select(
			sales_invoice.customer,
			sales_invoice.name,
			sales_invoice.posting_date,
			customer.customer_group,
			sales_invoice.grand_total,
			sales_invoice_item.warehouse,
		)
		.where(sales_invoice.docstatus == 1)
		.where(sales_invoice.posting_date[filters.from_date:filters.to_date])
		.groupby(group_by)
		.run(as_dict=True)
	)

	for item in data:
		#
		# For item info
		#
		itm_info = (
			frappe.qb.from_(sales_invoice_item)
			.left_join(sales_invoice).on(sales_invoice.name == sales_invoice_item.parent)
			.select(
				sales_invoice_item.item_code.as_("itm"),
				sales_invoice_item.qty,
				sales_invoice_item.parent.as_("si_name"),
				sales_invoice.customer.as_("cust"),
			)
			.where(sales_invoice.name == sales_invoice_item.parent)
			.where(sales_invoice.docstatus == 1)
			.run(as_dict=True)
		)
									
		item.item_no = ''
		item.quantity=''

		for co in itm_info:
			if co.si_name == item.name:
				item.item_no += '<a href="/desk#Form/Item/' + str(co.itm) + '">' + str(co.itm) + '</a>,' + ' '
				item.quantity += str(co.qty)	+ ', '

	return columns, data
