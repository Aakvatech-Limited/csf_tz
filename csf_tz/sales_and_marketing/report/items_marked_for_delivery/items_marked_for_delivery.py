# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = [
		{"fieldname": "customer_name", "label": _("Customer"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "customer_address",
			"label": _("Customer Address"),
			"fieldtype": "Small Text",
			"width": 200,
		},
		{"fieldname": "phone_number", "label": _("Phone Number"), "fieldtype": "Data", "width": 150},
		{"fieldname": "item_name", "label": _("Item"), "fieldtype": "Data", "width": 150},
		{"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Data", "width": 150},
		{"fieldname": "quantity", "label": _("Quantity"), "fieldtype": "Float", "width": 150},
		{"fieldname": "uom", "label": _("UOM"), "fieldtype": "Data", "width": 150},
		{"fieldname": "serial_no", "label": _("Serial Numbers"), "fieldtype": "Data", "width": 150},
		{"fieldname": "actual_quantity", "label": _("Actual Quantity"), "fieldtype": "Float", "width": 100},
		{
			"fieldname": "projected_quantity",
			"label": _("Projected Quantity"),
			"fieldtype": "Float",
			"width": 100,
		},
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "sales_invoice",
			"label": _("Sales Invoice"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150,
		},
		{
			"fieldname": "sales_order",
			"label": _("Sales Order"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 150,
		},
	]

	where = ""
	where_filter = {}

	if filters.warehouse:
		where += " AND sit.warehouse = %(warehouse)s"
		where_filter.update({"warehouse": filters.warehouse})

	if filters.item_group:
		where += " AND tabItem.item_group = %(item_group)s"
		where_filter.update({"item_group": filters.item_group})

	data = frappe.db.sql(
		"""SELECT
								si.customer_name,
								CONCAT(ta.address_line1,",", ta.city,',', ta.country) AS customer_address,
 								ta.phone AS phone_number,
								sit.item_name,
								sit.item_code,
								sit.serial_no,
								sit.qty AS quantity,
								sit.uom,
								sit.warehouse,
								si.name AS sales_invoice,
								so.name AS sales_order,
								`tabBin`.actual_qty AS actual_quantity,
								`tabBin`.projected_qty AS projected_quantity
							FROM
								(`tabSales Invoice Item`sit)
							LEFT JOIN
								(`tabSales Order` so)
								ON (sit.sales_order = so.name)
							LEFT JOIN
								(`tabSales Invoice` si)
								ON (sit.parent=si.name)
							LEFT JOIN
								`tabBin` ON (`tabBin`.item_code = sit.item_code
									and `tabBin`.warehouse = sit.warehouse)
							LEFT JOIN
								tabItem ON tabItem.item_code = sit.item_code
							LEFT JOIN
								(`tabAddress` ta) ON ta.name=(SELECT dl.parent
								FROM (`tabDynamic Link` dl)
								WHERE
									dl.parenttype='Address' AND dl.link_doctype='Customer' AND
									dl.link_name=si.customer ORDER BY ta.creation LIMIT 1
								)
							WHERE
							 	is_marked = 1 AND sit.delivered_qty < sit.qty AND si.docstatus = 1 AND si.status IN ('Submitted', 'Paid', 'Overdue', 'Unpaid')
							 	AND (SELECT name FROM `tabSales Invoice` WHERE return_against = si.name LIMIT 1) IS NULL"""
		+ where,
		where_filter,
		as_dict=1,
	)
	return columns, data
