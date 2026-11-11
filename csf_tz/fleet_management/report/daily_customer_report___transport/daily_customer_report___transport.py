# Copyright (c) 2013, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum
from csf_tz.fleet_management.trip_queries import get_offloaded_trips_query, get_trip_location_query
from csf_tz.utils.query_builder import get_latest_reporting_status_query
import ast
import datetime

def execute(filters=None):
	columns, data = [], []
	
	columns = [
		{
			"fieldname": "file_number",
			"label": _("File No"),
			"fieldtype": "Link",
			"options": "Vehicle Trip",
			"width": 100
		},
		{
			"fieldname": "client",
			"label": _("Client"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "order_date",
			"label": _("Order Date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "transporter_name",
			"label": _("Transporter Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "fleet_number",
			"label": _("Fleet Number"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "vehicle_plate_number",
			"label": _("Truck"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "trailer_plate_number",
			"label": _("Trailer"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "loading_capacity",
			"label": _("Loading Capacity"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "cargo_type",
			"label": _("Cargo Type"),
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
			"fieldname": "cargo_reference",
			"label": _("Cargo Ref"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "weight",
			"label": _("Weight"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "driver_name",
			"label": _("Driver Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "passport_number",
			"label": _("Passport Number"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "drivers_licence",
			"label": _("Drivers Licence"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "contact_no",
			"label": _("Contact Number"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "loading_point_arrival_date",
			"label": _("Loading Point Arrival date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "loading_date",
			"label": _("Loading Date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "loading_point_dispatch_date",
			"label": _("Loading Point Dispatch date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "border_arrival_date",
			"label": _("Border Arrival date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "border_dispatch_date",
			"label": _("Border Dispatch Date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "destination_arrival_date",
			"label": _("Destination Arrival Date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "offloading_date",
			"label": _("Offloading Date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "offloading_weight",
			"label": _("Offloaded Weight"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "offloading_ref",
			"label": _("Offloading Ref"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "vehicle_position",
			"label": _("Vehicle Position"),
			"fieldtype": "data",
			"width": 150
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "data",
			"width": 150
		}
	]
	
	today = datetime.date.today().strftime("%Y-%m-%d")
	yesterday =  datetime.date.today() - datetime.timedelta(1)
	day_before = datetime.date.today() - datetime.timedelta(2)
	yesterday = yesterday.strftime("%Y-%m-%d")
	day_before = day_before.strftime("%Y-%m-%d")
	
	vehicle_trip = frappe.qb.DocType("Vehicle Trip")
	offloading_dates = [today, yesterday, day_before]

	data_main = get_trip_query("main", "En Route", filters.customer).where(
		vehicle_trip.reference_doctype.isnotnull() & vehicle_trip.reference_docname.isnotnull()
	).run(as_dict=True)

	data_return = get_trip_query("return", "En Route - Returning", filters.customer).where(
		vehicle_trip.return_reference_doctype.isnotnull() & vehicle_trip.return_reference_docname.isnotnull()
	).run(as_dict=True)

	data_offloaded_main = get_trip_query("main", "En Route", filters.customer).where(
		vehicle_trip.name.isin(get_offloaded_trips_query("main_route_steps", offloading_dates))
	).run(as_dict=True)

	data_offloaded_return = get_trip_query("return", "En Route - Returning", filters.customer).where(
		vehicle_trip.name.isin(get_offloaded_trips_query("return_route_steps", offloading_dates))
	).run(as_dict=True)
	
	data_main = get_trip_data(data_main)				
	data_return = get_trip_data(data_return, True)
	data_offloaded_main = get_trip_data(data_offloaded_main)
	data_offloaded_return = get_trip_data(data_offloaded_return, True)
					
	data = data_main + data_return + data_offloaded_main + data_offloaded_return
	
	data = sorted(data, key=lambda k: k['file_number']) 
	
	return columns, data
	
def get_trip_data(trip_data, return_trip=False):
	if trip_data:
		for d in trip_data:
			trip = frappe.get_doc('Vehicle Trip', d.file_number)
			route_steps = []
			if return_trip:
				route_steps = trip.return_route_steps
			else:
				route_steps = trip.main_route_steps
				
			for step in route_steps:
				loading_point, border, offloading_point = False, False, False
				if step.location_type and step.location_type.upper() == 'LOADING POINT' and not loading_point:
					d['loading_point_arrival_date'] = step.get("arrival_date")
					d['loading_date'] = step.get("loading_date")
					d['loading_point_dispatch_date'] = step.get("departure_date")
					loading_point = True
				elif step.location_type and step.location_type.upper() == 'BORDER' and not border:
					d['border_arrival_date'] = step.get("arrival_date")
					d['border_dispatch_date'] = step.get("departure_date")
					border = True
				elif step.location_type and step.location_type.upper() == 'OFFLOADING POINT' and not offloading_point:
					d['offloading_date'] = step.get('offloading_date')
					d['destination_arrival_date'] = step.get('arrival_date')
					offloading_point = True
					
					
	return trip_data


def get_trip_query(leg, status, customer):
	vehicle_trip = frappe.qb.DocType("Vehicle Trip")
	transport_assignment = frappe.qb.DocType("Transport Assignment")
	transport_request = frappe.qb.DocType("Transport Request")
	query = (
		frappe.qb.from_(vehicle_trip)
		.left_join(transport_assignment)
		.on(vehicle_trip.reference_docname == transport_assignment.name)
		.left_join(transport_request)
		.on(transport_request.name == transport_assignment.parent)
		.select(
			vehicle_trip.name.as_("file_number"),
			vehicle_trip[f"{leg}_customer"].as_("client"),
			transport_request.request_received.as_("order_date"),
			get_transporter_name(vehicle_trip).as_("transporter_name"),
			vehicle_trip.vehicle_plate_number,
			vehicle_trip.trailer_plate_number,
			get_cargo_type(vehicle_trip, leg).as_("cargo_type"),
			vehicle_trip[f"{leg}_goods_description"].as_("cargo"),
			get_cargo_reference(vehicle_trip, leg).as_("cargo_reference"),
			get_cargo_weight(vehicle_trip, leg).as_("weight"),
			vehicle_trip.driver_name,
			vehicle_trip.passport_number,
			vehicle_trip[f"{leg}_offloading_weight"].as_("offloading_weight"),
			get_trip_location_query(vehicle_trip, leg).as_("vehicle_position"),
			get_latest_reporting_status_query(
				vehicle_trip.name, "Vehicle Trip", f"{leg}_reporting_status"
			).as_("remarks"),
		)
		.where(vehicle_trip.status == status)
	)
	if customer:
		query = query.where(vehicle_trip[f"{leg}_customer"] == customer)
	return query


def get_transporter_name(vehicle_trip):
	return (
		Case()
		.when(vehicle_trip.transporter_type == "Bravo", "Bravo Logistics")
		.when(vehicle_trip.transporter_type == "Sub-Contractor", vehicle_trip.sub_contractor)
	)


def get_cargo_type(vehicle_trip, leg):
	cargo_type = vehicle_trip[f"{leg}_cargo_type"]
	return Case().when(cargo_type == "Loose Cargo", "Loose").else_(cargo_type)


def get_cargo_reference(vehicle_trip, leg):
	cargo_details = frappe.qb.DocType("Cargo Details")
	container_number = (
		frappe.qb.from_(cargo_details)
		.select(cargo_details.container_number)
		.where(
			(cargo_details.parenttype == "Vehicle Trip")
			& (cargo_details.parent == vehicle_trip.name)
			& (cargo_details.parentfield == f"{leg}_cargo")
		)
		.limit(1)
	)
	return Case().when(vehicle_trip.main_cargo_type == "Loose Cargo", "Loose").else_(container_number)


def get_cargo_weight(vehicle_trip, leg):
	cargo_details = frappe.qb.DocType("Cargo Details")
	container_weight = (
		frappe.qb.from_(cargo_details)
		.select(Sum(cargo_details.net_weight))
		.where(
			(cargo_details.parent == vehicle_trip.name)
			& (cargo_details.parenttype == "Vehicle Trip")
			& (cargo_details.parentfield == f"{leg}_cargo")
		)
	)
	return (
		Case()
		.when(vehicle_trip[f"{leg}_cargo_type"] == "Container", container_weight)
		.else_(vehicle_trip[f"{leg}_loose_net_weight"])
	)
