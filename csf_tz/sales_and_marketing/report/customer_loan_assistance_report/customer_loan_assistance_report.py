# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []

	columns = [
		{
			"fieldname": "reference",
			"label": _("Reference"),
			"fieldtype": "Link",
			"options": "Customer Loan Assistance",
			"width": 150,
		},
		{
			"fieldname": "customer_type",
			"label": _("Lead / Customer"),
			"fieldtype": "Link",
			"options": "Doctype",
			"width": 150,
			"hidden": 1,
		},
		{
			"fieldname": "customer_reference",
			"label": _("Customer Reference"),
			"fieldtype": "Dynamic Link",
			"options": "customer_type",
			"width": 150,
		},
		{"fieldname": "customer_name", "label": _("Customer Name"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "loan_supplier",
			"label": _("Loan Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150,
		},
		{"fieldname": "start_date", "label": _("Start Date"), "fieldtype": "Date", "width": 150},
		{"fieldname": "end_date", "label": _("End Date"), "fieldtype": "Date", "width": 150},
		{
			"fieldname": "loan_status",
			"label": _("Loan Status"),
			"fieldtype": "Dynamic Link",
			"options": "customer_type",
			"width": 150,
		},
	]

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	where_filter = {
		"start_date": filters.from_date,
		"end_date": filters.to_date,
	}
	where = ""
	if filters.loan_supplier:
		where += "  AND loan_supplier = %(loan_supplier)s "
		where_filter.update({"loan_supplier": filters.loan_supplier})

	data = frappe.db.sql(
		"""SELECT
								name AS reference,
								CASE
									WHEN customer IS NOT NULL THEN 'Customer'
								ELSE 'Lead' END AS customer_type,
								CASE
									WHEN customer IS NOT NULL THEN customer
								ELSE lead END AS customer_reference,
								CASE
									WHEN customer IS NOT NULL THEN customer
								ELSE lead_name END AS customer_name,
								loan_supplier,
								DATE(creation) AS start_date,
								completion_date AS end_date,
								loan_status
							FROM
								`tabCustomer Loan Assistance`
							WHERE
								creation BETWEEN %(start_date)s AND %(end_date)s
							"""
		+ where,
		where_filter,
		as_dict=1,
	)
	return columns, data
