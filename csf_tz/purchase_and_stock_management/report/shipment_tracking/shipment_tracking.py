# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []

	columns = [
		{
			"fieldname": "order_no",
			"label": _("Order No"),
			"fieldtype": "Link",
			"options": "Order Tracking",
			"width": 150,
		},
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Project"},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
		},
		{
			"fieldname": "mode_of_transport",
			"label": _("Mode of Transport"),
			"fieldtype": "Data",
			"width": 150,
		},
		{"fieldname": "shipped_date", "label": _("Shipping Date"), "fieldtype": "Date", "width": 150},
		{
			"fieldname": "expected_arrival_date",
			"label": _("Expected Arrival Date"),
			"fieldtype": "Date",
			"width": 150,
		},
		{
			"fieldname": "arrival_date",
			"label": _("Arrival Date"),
			"fieldtype": "Date",
		},
		{"fieldname": "order_status", "label": _("Status"), "fieldtype": "Data", "width": 200},
		{"fieldname": "bl_number", "label": _("Bl No"), "fieldtype": "Data", "width": 150},
		{"fieldname": "container_no", "label": _("Container"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "container_size",
			"label": _("Container Size"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "no_of_packages",
			"label": _("No of Packages"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "clearing_completion_date",
			"label": _("Clearing Completion Date"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "delivered_date",
			"label": _("Delivered Date"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "offloading_date",
			"label": _("Off-Loading Date"),
			"fieldtype": "Date",
		},
	]

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	where_filter = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}
	where = ""
	if filters.order:
		where += "  AND tot.name = %(order)s "
		where_filter.update({"order": filters.order})

	if filters.supplier:
		where += "  AND tot.supplier = %(supplier)s "
		where_filter.update({"supplier": filters.supplier})

	data = frappe.db.sql(
		"""SELECT
								tot.name AS order_no,
								tot.supplier,
								tot.project,
								tot.shipped_date,
								tot.expected_arrival_date,
								tot.mode_of_transport,
								tot.bl_number,
								tot.arrival_date,
								tot.clearing_completion_date,
								tot.delivered_date,
								tot.offloading_date,
								/*tc.container_no,
								tc.size,
								tc.no_of_packages,*/

								(SELECT
										CONCAT(op.date, " : ", op.current_location, ":", op.status)
									FROM
										`tabOrder Progress` AS op
									WHERE
										tot.name = op.parent
									ORDER BY
										op.date DESC
									LIMIT 0,1
								) AS order_status
							FROM
								(`tabOrder Tracking` tot)
							/*LEFT JOIN
								(`tabContainer` tc)
								ON (tot.name = tc.parent)*/
							Where
								tot.expected_arrival_date BETWEEN %(from_date)s AND %(to_date)s
						 """
		+ where,
		where_filter,
		as_dict=1,
	)

	for order in data:
		#
		# For container info
		#
		container_info = frappe.db.sql(
			"""SELECT
										container_no, size,no_of_packages
									FROM
										(`tabContainer` tc)
									LEFT JOIN
										(`tabOrder Tracking` tot)
										ON (tot.name = tc.parent)
									WHERE
										tot.name = %(parent)s """,
			{
				"parent": order.order_no,
			},
			as_dict=1,
		)
		order.container_no = ""
		order.container_size = ""
		order.no_of_packages = ""

		for co in container_info:
			order.container_no += str(co.container_no) + ","
			order.container_size += str(co.size) + ","
			order.no_of_packages += str(co.no_of_packages) + ","

	return columns, data
