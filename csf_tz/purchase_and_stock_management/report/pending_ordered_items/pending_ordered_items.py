# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull


def execute(filters=None):
	columns, data = [], []
	columns = [
		{"fieldname": "name", "label": _("Purchase Order"), "fieldtype": "Link", "options": "Purchase Order"},
		{
			"fieldname": "transaction_date",
			"label": _("Date "),
			"fieldtype": "Date",
		},
		{
			"fieldname": "req_by",
			"label": _("Req By Date "),
			"fieldtype": "Date",
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
		},
		{"fieldname": "supplier_name", "label": _("Supplier Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
		},
		{"fieldname": "qty", "label": _("Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "received_qty", "label": _("Received Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "qty_to_receive", "label": _("Qty To Receive"), "fieldtype": "Float", "width": 150},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 200},
		{"fieldname": "brand", "label": _("Brand"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
	]
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	purchase_order = frappe.qb.DocType("Purchase Order")
	order_item = frappe.qb.DocType("Purchase Order Item")
	query = (
		frappe.qb.from_(purchase_order)
		.join(order_item)
		.on(order_item.parent == purchase_order.name)
		.select(
			purchase_order.name,
			purchase_order.transaction_date,
			order_item.schedule_date.as_("req_by"),
			purchase_order.supplier,
			purchase_order.supplier_name,
			order_item.project,
			order_item.item_code,
			order_item.qty,
			order_item.received_qty,
			(order_item.qty - IfNull(order_item.received_qty, 0)).as_("qty_to_receive"),
			order_item.warehouse,
			order_item.item_name,
			order_item.description,
			order_item.brand,
			purchase_order.company,
		)
		.where(purchase_order.docstatus == 1)
		.where(purchase_order.status.notin(["Stopped", "Closed"]))
		.where(IfNull(order_item.received_qty, 0) < IfNull(order_item.qty, 0))
		.where(purchase_order.transaction_date[filters.from_date : filters.to_date])
	)
	if filters.purchase_order:
		query = query.where(purchase_order.name == filters.purchase_order)
	if filters.item_code:
		query = query.where(order_item.item_code == filters.item_code)
	if filters.warehouse:
		query = query.where(order_item.warehouse == filters.warehouse)
	if filters.supplier:
		query = query.where(purchase_order.supplier == filters.supplier)

	data = query.run(as_dict=True)

	return columns, data
