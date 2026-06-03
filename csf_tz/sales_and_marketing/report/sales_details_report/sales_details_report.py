# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = [
		{"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 150},
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
			"width": 150,
		},
		{
			"fieldname": "item_no",
			"label": _("Item Sold"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"fieldname": "name",
			"label": _("Sales Invoice"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150,
		},
		{"fieldname": "grand_total", "label": _("Amount"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "quantity", "label": _("Quantity"), "fieldtype": "data", "width": 150},
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Data", "width": 150},
	]

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	where_filter = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}
	where = ""

	if filters.customer:
		where += " AND si.customer = %(customer)s"
		where_filter.update({"customer": filters.customer})

	if filters.warehouse:
		where += " AND sit.warehouse = %(warehouse)s"
		where_filter.update({"warehouse": filters.warehouse})

	if filters.cust_group:
		where += " AND tc.customer_group = %(cust_group)s"
		where_filter.update({"cust_group": filters.cust_group})

	data = frappe.db.sql(
		"""SELECT
								si.customer,
								si.name,
								si.posting_date,
								tc.customer_group,
								si.grand_total,
								sit.warehouse

							FROM
								(`tabSales Invoice` si)
							LEFT JOIN
								(`tabSales Invoice Item` sit)
								ON (si.name = sit.parent)
							LEFT JOIN
								(`tabCustomer` tc)
								ON (tc.customer_name=si.customer)
							WHERE
							 	si.docstatus = 1
							AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
							GROUP BY si.name
							"""
		+ where,
		where_filter,
		as_dict=1,
	)
	for item in data:
		#
		# For item info
		#
		itm_info = frappe.db.sql(
			"""SELECT
										sit.item_code as itm, sit.qty,
										sit.parent as si_name, si.customer as cust
									FROM
										(`tabSales Invoice Item` sit)
									LEFT JOIN
										(`tabSales Invoice` si)
										ON (si.name = sit.parent)
									WHERE
										si.name = sit.parent AND si.docstatus = 1									""",
			{
				"cust": item.customer,
			},
			as_dict=1,
		)
		item.item_no = ""
		item.quantity = ""

		for co in itm_info:
			if co.si_name == item.name:
				item.item_no += '<a href="/desk#Form/Item/' + str(co.itm) + '">' + str(co.itm) + "</a>," + " "
				item.quantity += str(co.qty) + ", "

	return columns, data
