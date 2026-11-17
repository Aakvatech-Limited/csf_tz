# Copyright (c) 2013, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
from frappe.query_builder import Case, Order
from frappe.query_builder.functions import Concat, Upper
from pypika.terms import Bracket
from csf_tz.fleet_management.trip_queries import get_case_by_joined_table
from csf_tz.utils.query_builder import get_latest_reporting_status_query
import ast
import datetime

def execute(filters=None):
	columns, data = [], []
	
	columns = [
		{
			"fieldname": "fleet_no",
			"label": _("Fleet No"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "reg_no",
			"label": _("Reg. No"),
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
			"fieldname": "contact",
			"label": _("Contact"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "cargo_type",
			"label": _("Cargo Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "destination",
			"label": _("Destination"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "client",
			"label": _("Client"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "route",
			"label": _("Route"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "dispatch_date",
			"label": _("Dispatch Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "offloading_date",
			"label": _("Offloading Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "position",
			"label": _("Position"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "next_cargo_allocation",
			"label": _("Next Cargo Allocation"),
			"fieldtype": "Data",
			"width": 100
		}
	]
	
	today = datetime.date.today().strftime("%Y-%m-%d")
	yesterday =  datetime.date.today() - datetime.timedelta(1)
	day_before = datetime.date.today() - datetime.timedelta(2)
	yesterday = yesterday.strftime("%Y-%m-%d")
	day_before = day_before.strftime("%Y-%m-%d")
	
	data = get_vehicle_status_query([today, yesterday, day_before]).run(as_dict=True)
	for row in data:
		if row.next_assigned_parenttype and row.next_assigned_parent:
			next_assigned = None
			if row.next_assigned_parenttype == 'Import':
				next_assigned = frappe.get_doc('Import', row.next_assigned_parent).customer
			elif row.next_assigned_parenttype == 'Transport Request':
				next_assigned = frappe.get_doc('Transport Request', row.next_assigned_parent).customer
			row.update({"next_cargo_allocation": next_assigned})
				
	return columns, data


def get_vehicle_status_query(recent_dates):
	vehicle = frappe.qb.DocType("Vehicle")
	trailer = frappe.qb.DocType("Trailer")
	employee = frappe.qb.DocType("Employee")
	transport_assignment = frappe.qb.DocType("Transport Assignment")
	transport_request = frappe.qb.DocType("Transport Request")
	main_trip = frappe.qb.DocType("Vehicle Trip").as_("main_trip")
	return_trip = frappe.qb.DocType("Vehicle Trip").as_("return_trip")
	main_trip_offloaded = frappe.qb.DocType("Vehicle Trip").as_("main_trip_offloaded")
	return_trip_offloaded = frappe.qb.DocType("Vehicle Trip").as_("return_trip_offloaded")
	trips = [(main_trip, "main"), (return_trip, "return"), (main_trip_offloaded, "main"), (return_trip_offloaded, "return")]
	return (
		frappe.qb.from_(vehicle)
		.left_join(trailer)
		.on(trailer.name == vehicle.default_trailer)
		.left_join(employee)
		.on(employee.name == vehicle.driver)
		.left_join(main_trip)
		.on((main_trip.vehicle == vehicle.name) & (main_trip.status == "En Route"))
		.left_join(return_trip)
		.on((return_trip.vehicle == vehicle.name) & (return_trip.status == "En Route - Returning"))
		.left_join(main_trip_offloaded)
		.on(get_offloaded_trip_condition(main_trip_offloaded, "main", vehicle, recent_dates))
		.left_join(return_trip_offloaded)
		.on(get_offloaded_trip_condition(return_trip_offloaded, "return", vehicle, recent_dates))
		.left_join(transport_assignment)
		.on(transport_assignment.name == get_next_assignment_query(vehicle))
		.left_join(transport_request)
		.on(
			(transport_request.name == transport_assignment.parent)
			& (transport_assignment.parenttype == "Transport Request")
		)
		.select(
			vehicle.fleet_number.as_("fleet_no"),
			Concat(vehicle.number_plate, "/", trailer.number_plate).as_("reg_no"),
			employee.employee_name.as_("driver_name"),
			employee.cell_number.as_("contact"),
			get_case_by_joined_table([(trip, trip[f"{leg}_goods_description"]) for trip, leg in trips]).as_("cargo_type"),
			get_case_by_joined_table([(trip, trip[f"{leg}_cargo_destination_city"]) for trip, leg in trips]).as_("destination"),
			get_case_by_joined_table([(trip, trip[f"{leg}_customer"]) for trip, leg in trips]).as_("client"),
			get_route_case(trips).as_("route"),
			get_case_by_joined_table(
				[(trip, get_route_step_date_query(trip, leg, "loading_date", "loading_date")) for trip, leg in trips]
			).as_("dispatch_date"),
			get_offloading_date_case(main_trip, return_trip, trips[2:]).as_("offloading_date"),
			get_case_by_joined_table(
				[
					(trip, get_latest_reporting_status_query(trip.name, "Vehicle Trip", f"{leg}_reporting_status"))
					for trip, leg in trips
				]
			).as_("position"),
			transport_assignment.parenttype.as_("next_assigned_parenttype"),
			transport_assignment.parent.as_("next_assigned_parent"),
		)
	)


def get_route_case(trips):
	case = Case()
	for trip_pair in (trips[:2], trips[2:]):
		for route, is_from_tanzania in (("Import", True), ("Export", False)):
			for trip, leg in trip_pair:
				case = case.when(get_route_condition(trip, leg, is_from_tanzania), route)
	return case


def get_route_condition(trip, leg, is_from_tanzania):
	origin_country = Upper(trip[f"{leg}_cargo_location_country"])
	destination_country = Upper(trip[f"{leg}_cargo_destination_country"])
	if is_from_tanzania:
		return (origin_country == "TANZANIA") & (destination_country != "TANZANIA")
	return (origin_country != "TANZANIA") & (destination_country == "TANZANIA")


def get_offloading_date_case(main_trip, return_trip, offloaded_trips):
	case = Case().when(main_trip.name.isnotnull() & return_trip.name.isnotnull(), None)
	for trip, leg in offloaded_trips:
		case = case.when(trip.name.isnotnull(), get_route_step_date_query(trip, leg, "offloading_date", "offloading_date"))
	return case


def get_offloaded_trip_condition(trip, leg, vehicle, recent_dates):
	loading_date = get_route_step_date_query(trip, leg, "loading_date", "offloading_date")
	return (
		(trip.vehicle == vehicle.name)
		& (trip.status == "Main Trip Offloaded")
		& Bracket(loading_date).isin(recent_dates)
	)


def get_route_step_date_query(trip, leg, fieldname, required_fieldname):
	route_steps = frappe.qb.DocType("Route Steps Table")
	return (
		frappe.qb.from_(route_steps)
		.select(route_steps[fieldname])
		.where(
			(route_steps.parent == trip.name)
			& (route_steps.parentfield == f"{leg}_route_steps")
			& route_steps[required_fieldname].isnotnull()
		)
		.limit(1)
	)


def get_next_assignment_query(vehicle):
	pending_assignment = frappe.qb.DocType("Transport Assignment").as_("pending_assignment")
	return (
		frappe.qb.from_(pending_assignment)
		.select(pending_assignment.name)
		.where(
			(pending_assignment.assigned_vehicle == vehicle.name)
			& (pending_assignment.status == "Not Processed")
		)
		.orderby(pending_assignment.expected_loading_date, order=Order.asc)
		.limit(1)
	)
