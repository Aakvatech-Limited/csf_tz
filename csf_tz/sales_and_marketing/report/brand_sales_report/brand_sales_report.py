# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = [
		{"fieldname": "posting_date", "label": _("Sale Date"), "fieldtype": "Date", "width": 150},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
		{
			"fieldname": "customer_address",
			"label": _("Customer Address"),
			"fieldtype": "Small Text",
			"width": 200,
		},
		{"fieldname": "contact", "label": _("Customer Contacts"), "fieldtype": "Small Text", "width": 150},
		{"fieldname": "itm", "label": _("Item Sold"), "fieldtype": "Link", "options": "Item", "width": 200},
		{
			"fieldname": "brand",
			"label": _("Brand"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150,
		},
		{"fieldname": "quantity", "label": _("Quantity"), "fieldtype": "data", "width": 150},
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

	if filters.brand:
		where += " AND ti.brand = %(brand)s"
		where_filter.update({"brand": filters.brand})

	data = frappe.db.sql(
		"""SELECT
								si.customer,
								si.name,
								si.posting_date,
								si.grand_total,
								sit.warehouse,
								sit.item_code as itm,
								sit.qty as quantity,
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
							 	si.docstatus = 1 AND ti.item_group <> 'Spare Parts'
							 	AND si.customer <> 'Guest' AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
							"""
		+ where,
		where_filter,
		as_dict=1,
	)
	for customer in data:
		address = []
		address_name = frappe.db.sql(
			"""SELECT
											dl.parent
										FROM
											(`tabDynamic Link` dl)
										WHERE
											dl.parenttype='Address' AND dl.link_doctype='Customer' AND dl.link_name= %(customer)s
										ORDER BY
											dl.creation
										LIMIT 1""",
			{"customer": customer.customer},
			as_dict=1,
		)
		if address_name:
			address = frappe.db.sql(
				"""SELECT
											CONCAT(ta.address_line1,",", ta.city,',', ta.country) AS customer_address,
											ta.phone AS contact
										FROM
											(`tabAddress` ta)
										WHERE
											ta.name = %(address_name)s""",
				{"address_name": address_name[0].parent},
				as_dict=1,
			)
		if address:
			customer.update({"customer_address": address[0].customer_address, "contact": address[0].contact})

	return columns, data
