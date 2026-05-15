# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


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
			"label": _("Date"),
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
			"label": _("Req By Date"),
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

	where_filter = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}
	where = ""
	if filters.sales_order:
		where += "  AND tso.name = %(sales_order)s "
		where_filter.update({"sales_order": filters.sales_order})
	if filters.item_code:
		where += "  AND so_itm.item_code = %(item_code)s "
		where_filter.update({"item_code": filters.item_code})
	if filters.customer:
		where += "  AND tso.customer = %(customer)s "
		where_filter.update({"customer": filters.customer})
	if filters.warehouse:
		where += "  AND so_itm.warehouse = %(warehouse)s "
		where_filter.update({"warehouse": filters.warehouse})

	data = frappe.db.sql(
		"""SELECT
								tso.name,
								tso.customer,
								tso.customer_name,
								tso.transaction_date,
								tso.project,
								so_itm.item_code,
								so_itm.qty,
								so_itm.delivered_qty,
								(so_itm.qty - ifnull(so_itm.delivered_qty, 0)) AS qty_to_deliver,
								so_itm.base_rate,
								so_itm.base_amount,
								((so_itm.qty - ifnull(so_itm.delivered_qty, 0))* so_itm.base_rate)
								AS amount_to_deliver,
								bin.actual_qty,
								bin.projected_qty,
								so_itm.delivery_date,
								DATEDIFF(CURDATE(),so_itm.delivery_date) AS delay_days,
								so_itm.item_name,
								so_itm.description,
								so_itm.item_group,
								so_itm.warehouse
							FROM
								(`tabSales Order` tso) JOIN (`tabSales Order Item` so_itm)
							LEFT JOIN
								(tabBin AS bin ) ON (bin.item_code = so_itm.item_code
 							and bin.warehouse = so_itm.warehouse)
							WHERE
								so_itm.parent = tso.name
							AND tso.docstatus = 1
							AND tso.status not in ("Stopped", "Closed")
							AND ifnull(so_itm.delivered_qty, 0) < ifnull(so_itm.qty, 0)
/*							ORDER BY tso.transaction_date
*/							 """
		+ where,
		where_filter,
		as_dict=1,
		as_list=1,
	)
	return columns, data
