# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = [
		{"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 200},
		{
			"fieldname": "total_qty",
			"label": _("Quantity"),
			"fieldtype": "Float",
		},
		{"fieldname": "quotations", "label": _("Quotations"), "fieldtype": "int", "width": 150},
		{"fieldname": "customers", "label": _("Customers"), "fieldtype": "Int", "width": 150},
		{"fieldname": "leads", "label": _("Leads"), "fieldtype": "Int", "width": 150},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 200,
		},
	]
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	where_filter = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}
	where = ""

	data = frappe.db.sql(
		"""SELECT
								tqi.item_code,
								tqi.item_name,
								SUM(tqi.qty) AS total_qty,
								COUNT(tq.name) AS quotations,
								COUNT(DISTINCT customer_quot.customer) AS customers,
								COUNT(DISTINCT tq.lead) AS leads,
								tqi.warehouse
							FROM
								(`tabQuotation Item` tqi)
							LEFT JOIN
								(`tabQuotation` tq) ON (tqi.parent = tq.name)
							LEFT JOIN
								(`tabQuotation` customer_quot) ON tqi.parent = customer_quot.name AND customer_quot.quotation_to = 'Customer'
							WHERE
								tq.docstatus = 1 AND tq.transaction_date BETWEEN %(from_date)s AND %(to_date)s
							GROUP BY tqi.item_code, tqi.warehouse
							"""
		+ where,
		where_filter,
		as_dict=1,
		as_list=1,
	)
	return columns, data
