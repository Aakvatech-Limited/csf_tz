# Copyright (c) 2013, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, getdate, cstr
from frappe import _
from frappe.query_builder import Case, Criterion
import ast
import datetime
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
from csf_tz.utils.query_builder import get_latest_reporting_status_query

def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "file_number",
			"label": _("File No"),
			"fieldtype": "Link",
			"options": "Border Clearance",
			"width": 100
		},
		{
			"fieldname": "client",
			"label": _("Client"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 100
		},
		{
			"fieldname": "consignee",
			"label": _("Consignee"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "crn_reference_number",
			"label": _("CRN Reference No"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "documents_received",
			"label": _("Documents Received"),
			"fieldtype": "Datetime",
			"width": 100
		},
		{
			"fieldname": "transporter",
			"label": _("Transporter"),
			"fieldtype": "Data",
			"width": 100
		},		
		{
			"fieldname": "trip_number",
			"label": _("Trip Number"),
			"fieldtype": "Link",
			"options": "Vehicle Trip",
			"width": 100
		},		
		{
			"fieldname": "vehicle_reg",
			"label": _("Vehicle Reg"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "trailer_reg",
			"label": _("Trailer Reg"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "driver_name",
			"label": _("Driver Name"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "cargo",
			"label": _("Cargo"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "container_size",
			"label": _("Container Size"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "weight",
			"label": _("Weight (kg)"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "bond_reference",
			"label": _("Bond Reference"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "cargo_origin",
			"label": _("Cargo Origin"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "cargo_destination",
			"label": _("Cargo Destination"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "border1_name",
			"label": _("Border 1 Name"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "border1_arrival",
			"label": _("Border 1 Arrival"),
			"fieldtype": "Datetime",
			"width": 100
		},
		{
			"fieldname": "border1_departure",
			"label": _("Border 1 Departure"),
			"fieldtype": "Datetime",
			"width": 100
		},
		{
			"fieldname": "border1_crossing",
			"label": _("Border 1 Crossing"),
			"fieldtype": "Datetime",
			"width": 100
		},
		{
			"fieldname": "border2_name",
			"label": _("Border 2 Name"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "border2_arrival",
			"label": _("Border 2 Arrival"),
			"fieldtype": "Datetime",
			"width": 100
		},
		{
			"fieldname": "border2_departure",
			"label": _("Border 2 Departure"),
			"fieldtype": "Datetime",
			"width": 100
		},
		{
			"fieldname": "border2_crossing",
			"label": _("Border 2 Crossing"),
			"fieldtype": "Datetime",
			"width": 100
		},
		{
			"fieldname": "arrival_offloading_point",
			"label": _("Arrival Offloading Point"),
			"fieldtype": "Datetime",
			"width": 100
		},
		{
			"fieldname": "offloading_datetime",
			"label": _("Offloading Date and Time"),
			"fieldtype": "Datetime",
			"width": 100
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 100
		}
	]
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	border_clearance = frappe.qb.DocType("Border Clearance")
	conditions = [
		border_clearance.documents_received >= filters.from_date,
		border_clearance.documents_received <= filters.to_date,
	]
		
	if filters.client:
		conditions.append(border_clearance.client == filters.client)
		
	if filters.type and filters.type == 'Import':
		conditions.append(border_clearance.clearance_type == 'Exit')
	elif filters.type and filters.type == 'Export':
		conditions.append(border_clearance.clearance_type == 'Entry')
		
	data = get_border_clearance_query().where(Criterion.all(conditions)).run(as_dict=True)
	return columns, data


def get_border_clearance_query():
	border_clearance = frappe.qb.DocType("Border Clearance")
	cargo = frappe.qb.DocType("Cargo Details")
	first_cargo = frappe.qb.DocType("Cargo Details").as_("first_cargo")
	first_cargo_name = (
		frappe.qb.from_(first_cargo)
		.select(first_cargo.name)
		.where(first_cargo.parent == border_clearance.name)
		.limit(1)
	)
	is_container = border_clearance.cargo_type == 'Container'
	is_loose_cargo = border_clearance.cargo_type == 'Loose Cargo'
	return (
		frappe.qb.from_(border_clearance)
		.left_join(cargo).on(cargo.name == first_cargo_name)
		.select(
			border_clearance.name.as_("file_number"),
			border_clearance.client,
			border_clearance.consignee,
			Case()
			.when(border_clearance.clearance_type == 'Entry', 'Export')
			.when(border_clearance.clearance_type == 'Exit', 'Import')
			.when(border_clearance.clearance_type == 'Pass Through', 'Pass Through')
			.as_("type"),
			border_clearance.crn_reference_number,
			border_clearance.documents_received,
			Case()
			.when(border_clearance.transporter_type == 'Bravo', 'Bravo')
			.else_(border_clearance.transporter_name)
			.as_("transporter"),
			border_clearance.trip_reference_no.as_("trip_number"),
			border_clearance.vehicle_plate_number.as_("vehicle_reg"),
			border_clearance.trailer_plate_number.as_("trailer_reg"),
			border_clearance.driver_name,
			border_clearance.cargo_category.as_("cargo"),
			Case()
			.when(is_container & cargo.container_size.isin(['40 FT GP', '40 OT', '40RF', '40 FT Heavy']), '40')
			.when(is_container & cargo.container_size.isin(['20 FT GP', '20 OT', '20RF']), '20')
			.when(is_loose_cargo, 'Loose Cargo')
			.as_("container_size"),
			Case()
			.when(is_container, cargo.net_weight)
			.when(is_loose_cargo, border_clearance.loose_net_weight)
			.as_("weight"),
			border_clearance.bond_ref_no.as_("bond_reference"),
			border_clearance.cargo_origin_country.as_("cargo_origin"),
			border_clearance.cargo_destination_exact.as_("cargo_destination"),
			border_clearance.border1_name,
			border_clearance.border1_arrival,
			border_clearance.border1_departure,
			border_clearance.border1_crossing,
			border_clearance.border2_name,
			border_clearance.border2_arrival,
			border_clearance.border2_departure,
			border_clearance.border2_crossing,
			border_clearance.offloading_point_arrival.as_("arrival_offloading_point"),
			border_clearance.offloading_datetime,
			get_latest_reporting_status_query(border_clearance.name, "Border Clearance").as_("remarks"),
		)
	)
