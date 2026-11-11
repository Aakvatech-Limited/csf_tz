# Copyright (c) 2013, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
import ast
from datetime import datetime
from frappe.desk.reportview import export_query
from frappe.desk.query_report import run
from frappe.desk.query_report import get_columns_dict
from six import string_types
import os, json
import openpyxl
from openpyxl.styles import Font
from openpyxl import load_workbook
from six import StringIO, string_types
from frappe.utils.xlsxutils import handle_html

def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "reference_docname",
			"label": _("Reference"),
			"fieldtype": "Link",
			"options": "Vehicle Trip",
			"width": 100
		},
		{
			"fieldname": "vehicle",
			"label": _("Vehicle"),
			"fieldtype": "Link",
			"options": "Vehicle",
			"width": 100
		},
		{
			"fieldname": "fuel_type",
			"label": _("Fuel Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "quantity",
			"label": _("Quantity (Litres)"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "cost_per_litre",
			"label": _("Cost Per Litre"),
			"fieldtype": "Currency",
			"width": 150,
			"options": "currency"
		},
		{
			"fieldname": "disburcement_type",
			"label": _("Disburcement Type"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150
		},
		{
			"fieldname": "fuel_request",
			"label": _("Fuel Request"),
			"fieldtype": "Link",
			"options": "Fuel Request",
			"width": 150
		}
	]
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))
		
	fuel_request = frappe.qb.DocType("Fuel Request")
	vehicle_trip = frappe.qb.DocType("Vehicle Trip")
	fuel_request_table = frappe.qb.DocType("Fuel Request Table")
	query = (
		frappe.qb.from_(fuel_request)
		.left_join(vehicle_trip)
		.on(fuel_request.reference_docname == vehicle_trip.name)
		.left_join(fuel_request_table)
		.on(fuel_request.reference_docname == fuel_request_table.parent)
		.select(
			fuel_request.reference_docname,
			vehicle_trip.vehicle,
			fuel_request_table.fuel_type,
			fuel_request_table.quantity,
			fuel_request_table.cost_per_litre,
			fuel_request_table.disburcement_type,
			fuel_request_table.supplier,
			fuel_request.name.as_("fuel_request"),
		)
		.where(fuel_request_table.approved_date.between(filters.from_date, filters.to_date))
	)
	if filters.vehicle:
		query = query.where(vehicle_trip.vehicle == filters.vehicle)

	if filters.disburcement_type:
		query = query.where(fuel_request_table.disburcement_type == filters.disburcement_type)

	data = query.run(as_dict=True)
	return columns, data
