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
from frappe.query_builder import Case, Field
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Concat
from csf_tz.utils.query_builder import get_expenses_total_query
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
			"fieldname": "reference",
			"label": _("Reference"),
			"fieldtype": "Link",
			"options": "Vehicle Trip",
			"width": 100
		},
		{
			"fieldname": "trip_type",
			"label": _("Trip Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 100
		},
		{
			"fieldname": "transporter_type",
			"label": _("Transporter Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "transporter_name",
			"label": _("Transporter Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "vehicle_plate_number",
			"label": _("Vehicle"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "trailer_plate_number",
			"label": _("Trailer"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "driver_name",
			"label": _("Driver"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "cargo",
			"label": _("Cargo"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "source_location",
			"label": _("Source"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "destination_location",
			"label": _("Destination"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "eta",
			"label": _("ETA"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "trip_expenses_usd",
			"label": _("Trip Expenses (USD)"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "trip_expenses_tzs",
			"label": _("Trip Expenses (TZS)"),
			"fieldtype": "Float",
			"width": 120
		}
	]
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))
		
	main_trips = get_trip_query(filters, "Main Trip", "main")
	return_trips = get_trip_query(filters, "Return Trip", "return")
	data = main_trips.union_all(return_trips).orderby(Field("reference")).run(as_dict=True)
	return columns, data


def get_trip_query(filters, trip_type, leg):
	vehicle_trip = frappe.qb.DocType("Vehicle Trip")
	reference_prefix = "return_" if leg == "return" else ""
	transporter_name = (
		Case()
		.when(vehicle_trip.transporter_type == "Bravo", "Bravo")
		.else_(vehicle_trip.sub_contractor)
	)
	source_location = Concat(
		vehicle_trip[f"{leg}_loading_point"], "-",
		vehicle_trip[f"{leg}_cargo_location_city"], "-",
		vehicle_trip[f"{leg}_cargo_location_country"],
	)
	destination_location = Concat(
		vehicle_trip[f"{leg}_offloading_point"], "-",
		vehicle_trip[f"{leg}_cargo_destination_city"], "-",
		vehicle_trip[f"{leg}_cargo_destination_country"],
	)
	query = (
		frappe.qb.from_(vehicle_trip)
		.select(
			vehicle_trip.name.as_("reference"),
			ConstantColumn(trip_type).as_("trip_type"),
			vehicle_trip[f"{leg}_customer"].as_("customer"),
			vehicle_trip.transporter_type,
			transporter_name.as_("transporter_name"),
			vehicle_trip.vehicle_plate_number,
			vehicle_trip.trailer_plate_number,
			vehicle_trip.driver_name,
			vehicle_trip[f"{leg}_cargo_category"].as_("cargo"),
			source_location.as_("source_location"),
			destination_location.as_("destination_location"),
			vehicle_trip[f"{leg}_eta"].as_("eta"),
			vehicle_trip.status,
			get_expenses_total_query(vehicle_trip.name, "Vehicle Trip", "USD").as_("trip_expenses_usd"),
			get_expenses_total_query(vehicle_trip.name, "Vehicle Trip", "TZS").as_("trip_expenses_tzs"),
		)
		.where(
			vehicle_trip[f"{reference_prefix}reference_doctype"].isnotnull()
			& vehicle_trip[f"{reference_prefix}reference_docname"].isnotnull()
			& vehicle_trip[f"{reference_prefix}start_date"].between(filters.from_date, filters.to_date)
		)
	)
	if filters.status:
		query = query.where(vehicle_trip.status == filters.status)
	return query
