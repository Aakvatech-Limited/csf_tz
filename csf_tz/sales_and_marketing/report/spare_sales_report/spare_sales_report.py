# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns()
	item_list = get_items(filters)

	data = []
	for d in item_list:
		row = [
			d.posting_date,
			d.itm,
			d.item_name,
			d.customer,
			d.warehouse,
			d.quantity,
			d.amount,
			d.brand,
			d.name,
		]
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
		_("Invoice") + ":Link/Sales Invoice:120",
	]

	return columns


def get_items(filters):
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	where_filter = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}
	where = ""

	if filters.brand:
		where += " AND ti.brand = %(brand)s"
		where_filter.update({"brand": filters.brand})

	if filters.shop:
		where += " AND sit.warehouse = %(shop)s"
		where_filter.update({"shop": filters.shop})

	return frappe.db.sql(
		"""SELECT
								si.customer,
								si.name,
								si.posting_date,
								si.grand_total,
								sit.warehouse,
								sit.item_code as itm,
								sit.item_name,
								sit.qty as quantity,
								sit.amount,
								ti.brand as brand,
								sit.parent as si_name,
								si.customer as cust
							FROM
								(`tabSales Invoice Item` sit)
							LEFT JOIN
								(`tabSales Invoice` si)
								ON (si.name = sit.parent)
							LEFT JOIN
								(`tabItem` ti)
								ON (ti.item_code = sit.item_code)
							WHERE
							 	si.docstatus = 1 AND ti.item_group = 'Spare Parts'
							 	AND si.customer = 'Guest' AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
							ORDER BY si.posting_date
							"""
		+ where,
		where_filter,
		as_dict=1,
	)
