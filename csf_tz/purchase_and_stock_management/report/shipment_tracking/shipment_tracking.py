# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Concat

def execute(filters=None):
	columns, data = [], []
	
	columns = [
		{
		 	"fieldname": "order_no",
		 	"label": _("Order No"),
		 	"fieldtype": "Link",
		 	"options": "Order Tracking",
		 	"width": 150
		},	
		{
			"fieldname": "project",
			"label" : _("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
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
		 	"width": 150
		},	
		{
			"fieldname": "shipped_date",
			"label": _("Shipping Date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "expected_arrival_date",
			"label": _("Expected Arrival Date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "arrival_date",
			"label": _("Arrival Date"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "order_status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "bl_number",
			"label": _("Bl No"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "container_no",
			"label": _("Container"),
			"fieldtype": "Data",
			"width": 150
		},
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

	order_tracking = frappe.qb.DocType("Order Tracking")
	order_progress = frappe.qb.DocType("Order Progress")
	container = frappe.qb.DocType("Container")

	latest_order_status = (
		frappe.qb.from_(order_progress)
		.select(Concat(order_progress.date, " : ", order_progress.current_location, ":", order_progress.status))
		.where(order_tracking.name == order_progress.parent)
		.orderby(order_progress.date, order=Order.desc)
		.limit(1)
	)

	query = (
		frappe.qb.from_(order_tracking)
		.select(
			order_tracking.name.as_("order_no"),
			order_tracking.supplier,
			order_tracking.project,
			order_tracking.shipped_date,
			order_tracking.expected_arrival_date,
			order_tracking.mode_of_transport,
			order_tracking.bl_number,
			order_tracking.arrival_date,
			order_tracking.clearing_completion_date,
			order_tracking.delivered_date,
			order_tracking.offloading_date,
			latest_order_status.as_("order_status"),
		)
		.where(order_tracking.expected_arrival_date[filters.from_date:filters.to_date])
	)

	if filters.order:
		query = query.where(order_tracking.name == filters.order)
	
	if filters.supplier:
		query = query.where(order_tracking.supplier == filters.supplier)
	
	data = query.run(as_dict=1)

	for order in data:
		#
		# For container info
		#
		container_info = (
			frappe.qb.from_(container)
			.left_join(order_tracking)
			.on(order_tracking.name == container.parent)
			.select(container.container_no, container.size, container.no_of_packages)
			.where(order_tracking.name == order.order_no)
		).run(as_dict=1)
		order.container_no = ''
		order.container_size=''
		order.no_of_packages=''

		for co in container_info:
			order.container_no += str(co.container_no) + ','
			order.container_size += str(co.size) + ','
			order.no_of_packages += str(co.no_of_packages)	+ ','

	return columns, data
