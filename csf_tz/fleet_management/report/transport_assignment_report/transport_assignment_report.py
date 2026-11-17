# Copyright (c) 2013, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder import Case, Field, Order
from csf_tz.fleet_management.trip_queries import get_case_by_joined_table, get_trip_location_query
from csf_tz.utils.query_builder import get_latest_reporting_status_query
import ast
import datetime
import time

def execute(filters=None):
	columns, data = [], []
	
	columns = [
		{
			"fieldname": "trip_no",
			"label": _("Trip No"),
			"fieldtype": "Link",
			"options": "Vehicle Trip",
			"width": 100
		},
		{
			"fieldname": "tcustomer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 100
		},
		{
			"fieldname": "fleet_no",
			"label": _("Fleet No"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "truck_no",
			"label": _("Truck No"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "trailer_no",
			"label": _("Trailer No"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "driver",
			"label": _("Driver"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "contact_no",
			"label": _("Contact Number"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "passport_no",
			"label": _("Passport Number"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "driving_licence",
			"label": _("Driving Licence"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "cargo_description",
			"label": _("Cargo Description"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "quantity",
			"label": _("Quantity"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "loading_date",
			"label": _("Loading Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "departure_date",
			"label": _("Departure Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "eta_border",
			"label": _("ETA Border"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "ata_border",
			"label": _("ATA Border"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "departure_border",
			"label": _("Departure Border"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "days_at_border",
			"label": _("Days at Border"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "offloading_date",
			"label": _("Offloading Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "trip_days",
			"label": _("Trip Days"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "current_position",
			"label": _("Current Position"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 200
		}
	]
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))
	
	query = get_transport_assignment_query(filters.from_date, filters.to_date)
	if filters.customer:
		query = query.having(Field("tcustomer") == filters.customer)

	data = query.run(as_dict=True)
						
	for row in data:
		if row.ata_border and row.departure_border:
			row.update({"days_at_border": (row.ata_border-row.departure_border).days})
		
		if row.loading_date and row.offloading_date:
			row.update({"trip_days": (row.offloading_date-row.loading_date).days})
	
	return columns, data


def get_transport_assignment_query(from_date, to_date):
	transport_assignment = frappe.qb.DocType("Transport Assignment")
	main_trip = frappe.qb.DocType("Vehicle Trip").as_("main_trip")
	return_trip = frappe.qb.DocType("Vehicle Trip").as_("return_trip")
	transport_request = frappe.qb.DocType("Transport Request").as_("transport_request")
	import_request = frappe.qb.DocType("Transport Request").as_("import_request")
	vehicle = frappe.qb.DocType("Vehicle")
	cargo_details = frappe.qb.DocType("Cargo Details")
	trips = [(main_trip, "main"), (return_trip, "return")]
	requests = [transport_request, import_request]
	return (
		frappe.qb.from_(transport_assignment)
		.left_join(main_trip)
		.on(main_trip.reference_docname == transport_assignment.name)
		.left_join(return_trip)
		.on(return_trip.return_reference_docname == transport_assignment.name)
		.left_join(transport_request)
		.on(
			(transport_request.name == transport_assignment.parent)
			& (transport_assignment.parenttype == "Transport Request")
		)
		.left_join(import_request)
		.on(
			(import_request.reference_docname == transport_assignment.parent)
			& (transport_assignment.parenttype == "Import")
			& import_request.file_number.isnotnull()
		)
		.left_join(vehicle)
		.on((vehicle.name == transport_assignment.assigned_vehicle) & (transport_assignment.transporter_type == "Bravo"))
		.left_join(cargo_details)
		.on(
			(cargo_details.container_number == transport_assignment.container_number)
			& (cargo_details.parent == transport_assignment.parent)
		)
		.select(
			get_case_by_joined_table([(main_trip, main_trip.name), (return_trip, return_trip.name)]).as_("trip_no"),
			get_case_by_joined_table(
				[(transport_request, transport_request.customer), (import_request, import_request.customer)]
			).as_("tcustomer"),
			vehicle.fleet_number.as_("fleet_no"),
			transport_assignment.vehicle_plate_number.as_("truck_no"),
			transport_assignment.trailer_plate_number.as_("trailer_no"),
			transport_assignment.driver_name.as_("driver"),
			transport_assignment.passport_number.as_("passport_no"),
			get_case_by_joined_table(
				[
					(transport_request, transport_request.cargo_description),
					(import_request, import_request.cargo_description),
				]
			).as_("cargo_description"),
			get_quantity_case(requests, cargo_details, transport_assignment).as_("quantity"),
			get_route_step_case(trips, "loading_date").as_("loading_date"),
			get_route_step_case(trips, "departure_date").as_("departure_date"),
			get_case_by_joined_table(
				[(trip, get_border_step_query(trip, leg, "arrival_date")) for trip, leg in trips]
			).as_("ata_border"),
			get_case_by_joined_table(
				[(trip, get_border_step_query(trip, leg, "departure_date")) for trip, leg in trips]
			).as_("departure_border"),
			get_route_step_case(trips, "offloading_date").as_("offloading_date"),
			get_case_by_joined_table(
				[(trip, get_trip_location_query(trip, leg)) for trip, leg in trips]
			).as_("current_position"),
			get_case_by_joined_table(
				[
					(trip, get_latest_reporting_status_query(trip.name, "Vehicle Trip", f"{leg}_reporting_status"))
					for trip, leg in trips
				]
			).as_("remarks"),
		)
		.where(transport_assignment.expected_loading_date.between(from_date, to_date))
	)


def get_quantity_case(requests, cargo_details, transport_assignment):
	case = Case()
	for request in requests:
		case = case.when(
			request.name.isnotnull()
			& (request.cargo_type == "Container")
			& cargo_details.net_weight.isnotnull()
			& (cargo_details.net_weight > 0),
			cargo_details.net_weight / 1000,
		).when(
			request.name.isnotnull() & (request.cargo_type == "Loose Cargo") & (request.unit == "TONNES"),
			transport_assignment.amount,
		)
	return case


def get_route_step_case(trips, fieldname):
	route_steps = frappe.qb.DocType("Route Steps Table")
	case = Case()
	for trip, leg in trips:
		first_step_value = (
			frappe.qb.from_(route_steps)
			.select(route_steps[fieldname])
			.where(
				(route_steps.parent == trip.name)
				& (route_steps.parentfield == f"{leg}_route_steps")
				& route_steps[fieldname].isnotnull()
			)
			.limit(1)
		)
		case = case.when(trip.name.isnotnull(), first_step_value)
	return case


def get_border_step_query(trip, leg, fieldname):
	route_steps = frappe.qb.DocType("Route Steps Table")
	return (
		frappe.qb.from_(route_steps)
		.select(route_steps[fieldname])
		.where(
			(route_steps.parent == trip.name)
			& (route_steps.parentfield == f"{leg}_route_steps")
			& (route_steps.location_type == "BORDER")
		)
		.orderby(route_steps[fieldname], order=Order.asc)
		.limit(1)
	)
