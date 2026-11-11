# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import CustomFunction
from frappe.query_builder.functions import CurDate, IfNull

DateDiff = CustomFunction("DATEDIFF", ["end_date", "start_date"])


def execute(filters=None):
	columns, data = [], []
	columns = [
		{"fieldname": "name", "label": _("Sales Order"), "fieldtype": "Link", "options": "Sales Order"},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
		},
		{"fieldname": "customer_name", "label": _("Customer Name"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "transaction_date",
			"label": _("Date "),
			"fieldtype": "Date",
		},
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
		},
		{
			"fieldname": "req_by",
			"label": _("Req By Date "),
			"fieldtype": "Date",
		},
		{"fieldname": "qty", "label": _("Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "delivered_qty", "label": _("Delivered Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "qty_to_deliver", "label": _("Qty to Deliver"), "fieldtype": "Float", "width": 150},
		{"fieldname": "base_rate", "label": _("Rate"), "fieldtype": "Float", "width": 150},
		{"fieldname": "base_amount", "label": _("Amount"), "fieldtype": "Float", "width": 150},
		{
			"fieldname": "amount_to_deliver",
			"label": _("Amount To Deliver"),
			"fieldtype": "Float",
			"width": 150,
		},
		{"fieldname": "actual_qty", "label": _("Available Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "projected_qty", "label": _("Projected Qty"), "fieldtype": "Float", "width": 150},
		{"fieldname": "delivery_date", "label": _("Item Delivery Date"), "fieldtype": "Date", "width": 150},
		{"fieldname": "delay_days", "label": _("Delay Days"), "fieldtype": "Int", "width": 150},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 200},
		{"fieldname": "item_group", "label": _("Item Group"), "fieldtype": "Data", "width": 200},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
	]
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	sales_order = frappe.qb.DocType("Sales Order")
	order_item = frappe.qb.DocType("Sales Order Item")
	stock_bin = frappe.qb.DocType("Bin")
	qty_to_deliver = order_item.qty - IfNull(order_item.delivered_qty, 0)
	query = (
		frappe.qb.from_(sales_order)
		.join(order_item)
		.on(order_item.parent == sales_order.name)
		.left_join(stock_bin)
		.on((stock_bin.item_code == order_item.item_code) & (stock_bin.warehouse == order_item.warehouse))
		.select(
			sales_order.name,
			sales_order.customer,
			sales_order.customer_name,
			sales_order.transaction_date,
			sales_order.project,
			order_item.item_code,
			order_item.qty,
			order_item.delivered_qty,
			qty_to_deliver.as_("qty_to_deliver"),
			order_item.base_rate,
			order_item.base_amount,
			(qty_to_deliver * order_item.base_rate).as_("amount_to_deliver"),
			stock_bin.actual_qty,
			stock_bin.projected_qty,
			order_item.delivery_date,
			DateDiff(CurDate(), order_item.delivery_date).as_("delay_days"),
			order_item.item_name,
			order_item.description,
			order_item.item_group,
			order_item.warehouse,
		)
		.where(sales_order.docstatus == 1)
		.where(sales_order.status.notin(["Stopped", "Closed"]))
		.where(IfNull(order_item.delivered_qty, 0) < IfNull(order_item.qty, 0))
	)
	if filters.sales_order:
		query = query.where(sales_order.name == filters.sales_order)
	if filters.item_code:
		query = query.where(order_item.item_code == filters.item_code)
	if filters.customer:
		query = query.where(sales_order.customer == filters.customer)
	if filters.warehouse:
		query = query.where(order_item.warehouse == filters.warehouse)

	data = query.run(as_dict=True)

	return columns, data
