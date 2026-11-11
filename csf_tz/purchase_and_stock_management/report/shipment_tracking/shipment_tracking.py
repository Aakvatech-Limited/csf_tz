# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	order_track = frappe.qb.DocType("Order Track")
	query = (
		frappe.qb.from_(order_track)
		.select(
			order_track.name.as_("order_no"),
			order_track.supplier,
			order_track.supplier_type,
			order_track.shipped_date,
			order_track.expected_arrival_date,
			order_track.mode_of_transport,
			order_track.bl_number,
			order_track.arrival_date,
			order_track.discharged_date,
			order_track.clearing_company,
			order_track.expected_clearing_completion_date,
			order_track.clearing_completion_date,
		)
		.where(order_track.expected_arrival_date[filters.from_date : filters.to_date])
	)
	if filters.order:
		query = query.where(order_track.name == filters.order)

	if filters.supplier:
		query = query.where(order_track.supplier == filters.supplier)

	data = query.run(as_dict=True)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "order_no",
			"label": _("Order No"),
			"fieldtype": "Link",
			"options": "Order Track",
			"width": 150,
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150,
		},
		{"fieldname": "supplier_type", "label": _("Supplier Type"), "fieldtype": "Data", "width": 150},
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
		{"fieldname": "arrival_date", "label": _("Arrival Date"), "fieldtype": "Date", "width": 120},
		{"fieldname": "discharged_date", "label": _("Discharged Date"), "fieldtype": "Date", "width": 120},
		{"fieldname": "bl_number", "label": _("Bl No"), "fieldtype": "Data", "width": 150},
		{"fieldname": "clearing_company", "label": _("Clearing Company"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "expected_clearing_completion_date",
			"label": _("Expected Clearing Completion Date"),
			"fieldtype": "Date",
			"width": 150,
		},
		{
			"fieldname": "clearing_completion_date",
			"label": _("Clearing Completion Date"),
			"fieldtype": "Date",
			"width": 150,
		},
	]
