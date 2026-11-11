# Copyright (c) 2013, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Concat
import ast
import datetime
import time

def execute(filters=None):
	columns, data = [], []
	
	columns = [
		{
			"fieldname": "reference",
			"label": _("Reference"),
			"fieldtype": "Link",
			"options": "Border Clearance",
			"width": 100
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "transporter",
			"label": _("Transporter"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "truck",
			"label": _("Truck\Trailer"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "cargo",
			"label": _("Cargo"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "border",
			"label": _("Border"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "border_date_time",
			"label": _("Border Crossing Date and Time"),
			"fieldtype": "Datatime",
			"width": 150
		}
	]
	
	
	border_clearance = frappe.qb.DocType("Border Clearance")
	data = (
		frappe.qb.from_(border_clearance)
		.select(
			border_clearance.name.as_("reference"),
			border_clearance.client.as_("customer"),
			border_clearance.cargo_destination_exact.as_("warehouse"),
			Case()
			.when(border_clearance.transporter_type == 'Other', border_clearance.transporter_name)
			.else_('Bravo')
			.as_("transporter"),
			Concat(border_clearance.vehicle_plate_number, '/', border_clearance.trailer_plate_number).as_("truck"),
			border_clearance.cargo_description.as_("cargo"),
			get_last_border_case(
				border_clearance,
				[
					border_clearance.border1_name,
					border_clearance.border2_name,
					border_clearance.border3_name,
					border_clearance.border4_name,
				],
			).as_("border"),
			get_last_border_case(
				border_clearance,
				[
					border_clearance.border1_crossing,
					border_clearance.border2_crossing,
					border_clearance.border3_crossing,
					border_clearance.border4_crossing,
				],
			).as_("border_date_time"),
		)
		.where(border_clearance.cargo_destination_country == 'Tanzania')
		.where(border_clearance.offloading_datetime.isnull())
		.run(as_dict=True)
	)
	
	
	return columns, data


def get_last_border_case(border_clearance, border_fields):
	last_border = Case()
	for border_number, border_field in enumerate(border_fields, start=1):
		last_border = last_border.when(border_clearance.no_of_borders == border_number, border_field)
	return last_border
