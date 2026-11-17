# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder.functions import IfNull


def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
		},
		{
			"fieldname": "item_name",
			"label": _("Item Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
		},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "qty",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "uom",
			"label": _("UOM"),
			"fieldtype": "Link",
			"options": "UOM",
			"width": 80

		},
		{
			"fieldname": "base_rate",
			"label": _("Rate"),
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"fieldname": "base_amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"fieldname": "name",
			"label" : _("Purchase Order"),
			"fieldtype": "Link",
			"options": "Purchase Order"
		},
		{
			"fieldname": "transaction_date",
			"label": _("Date "),
			"fieldtype": "Date",
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
		},
		{
			"fieldname": "supplier_name",
			"label": _("Supplier Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Data",
			"width": 150
		},	
		{
			"fieldname": "received_qty",
			"label": _("Received Qty"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 150
		},
		
	]
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	purchase_order = frappe.qb.DocType("Purchase Order")
	purchase_order_item = frappe.qb.DocType("Purchase Order Item")
	supplier = frappe.qb.DocType("Supplier")
	query = (
		frappe.qb.from_(purchase_order)
		.join(purchase_order_item)
		.on(purchase_order_item.parent == purchase_order.name)
		.join(supplier)
		.on(purchase_order.supplier == supplier.name)
		.select(
			purchase_order_item.item_code,
			purchase_order_item.item_name,
			purchase_order_item.item_group,
			purchase_order_item.description,
			purchase_order_item.qty,
			purchase_order_item.uom,
			purchase_order_item.base_rate,
			purchase_order_item.base_amount,
			purchase_order.name,
			purchase_order.transaction_date,
			purchase_order.supplier,
			supplier.supplier_name,
			purchase_order_item.project,
			IfNull(purchase_order_item.received_qty, 0).as_("received_qty"),
			purchase_order.company,
		)
		.where(purchase_order.transaction_date[filters.from_date:filters.to_date])
		.where(purchase_order.docstatus == 1)
	)

	if filters.purchase_order:
		query = query.where(purchase_order.name == filters.purchase_order)
	if filters.item_code:
		query = query.where(purchase_order_item.item_code == filters.item_code)
	if filters.supplier:
		query = query.where(purchase_order.supplier == filters.supplier)

	data = query.run(as_dict=1)

	return columns, data
