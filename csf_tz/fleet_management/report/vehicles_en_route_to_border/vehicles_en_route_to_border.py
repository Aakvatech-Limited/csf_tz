# Copyright (c) 2013, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder import Field, Order
from frappe.query_builder.functions import Concat, DateFormat, Upper
from csf_tz.fleet_management.trip_queries import get_case_by_joined_table
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
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "vehicle",
			"label": _("Vehicle/Trailer"),
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
			"fieldname": "border_name",
			"label": _("Border Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "eta_at_border",
			"label": _("ETA at Border"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "dispatch_date",
			"label": _("Dispatch Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "last_reported_position",
			"label": _("Last Reported Position"),
			"fieldtype": "Data",
			"width": 450
		}
	]
	
	
	query = get_vehicles_at_border_query()
	if filters.border:
		query = query.having(Field("border_name") == filters.border)

	data = query.orderby(Field("dispatch_date"), order=Order.asc).run(as_dict=True)
							
	for row in data:
		if row.route:
			route = frappe.get_doc('Trip Route', row.route)
			for location in route.trip_steps:
				if location.location == row.border_name:
					if location.distance and location.distance != 0:
						days_to_add = location.distance/340
						if row.dispatch_date:
							row.update({"eta_at_border": row.dispatch_date + datetime.timedelta(days=days_to_add)})
	
	return columns, data


def get_vehicles_at_border_query():
	route_steps = frappe.qb.DocType("Route Steps Table")
	main_trip = frappe.qb.DocType("Vehicle Trip").as_("main_trip")
	return_trip = frappe.qb.DocType("Vehicle Trip").as_("return_trip")
	main_loading_point = frappe.qb.DocType("Route Steps Table").as_("main_loading_point")
	return_loading_point = frappe.qb.DocType("Route Steps Table").as_("return_loading_point")
	trips = [(main_trip, "main"), (return_trip, "return")]
	return (
		frappe.qb.from_(route_steps)
		.left_join(main_trip)
		.on(get_trip_join_condition(main_trip, route_steps, "main_route_steps"))
		.left_join(return_trip)
		.on(get_trip_join_condition(return_trip, route_steps, "return_route_steps"))
		.left_join(main_loading_point)
		.on(main_loading_point.name == get_loading_point_query(main_trip, main_loading_point, "main_route_steps"))
		.left_join(return_loading_point)
		.on(return_loading_point.name == get_loading_point_query(return_trip, return_loading_point, "return_route_steps"))
		.select(
			get_case_by_joined_table([(main_trip, main_trip.name), (return_trip, return_trip.name)]).as_("trip_no"),
			get_case_by_joined_table(
				[(main_trip, main_trip.main_customer), (return_trip, return_trip.return_customer)]
			).as_("customer"),
			get_case_by_joined_table(
				[(trip, Concat(trip.vehicle_plate_number, "/", trip.trailer_plate_number)) for trip, leg in trips]
			).as_("vehicle"),
			get_case_by_joined_table(
				[(main_trip, main_trip.main_goods_description), (return_trip, return_trip.return_goods_description)]
			).as_("cargo"),
			route_steps.location.as_("border_name"),
			get_case_by_joined_table([(main_trip, main_trip.main_route), (return_trip, return_trip.return_route)]).as_("route"),
			get_case_by_joined_table(
				[
					(main_loading_point, main_loading_point.departure_date),
					(return_loading_point, return_loading_point.departure_date),
				]
			).as_("dispatch_date"),
			get_case_by_joined_table(
				[(trip, get_last_position_query(trip, leg)) for trip, leg in trips]
			).as_("last_reported_position"),
		)
		.where(
			(Upper(route_steps.location_type) == "BORDER")
			& route_steps.arrival_date.isnull()
			& ((main_trip.status == "En Route") | (return_trip.status == "En Route - Returning"))
		)
	)


def get_trip_join_condition(trip, route_steps, parentfield):
	return (
		(trip.name == route_steps.parent)
		& (route_steps.parenttype == "Vehicle Trip")
		& (route_steps.parentfield == parentfield)
	)


def get_loading_point_query(trip, loading_point, parentfield):
	route_step = frappe.qb.DocType("Route Steps Table").as_("route_step")
	return (
		frappe.qb.from_(route_step)
		.select(route_step.name)
		.where(
			(route_step.parent == trip.name)
			& (loading_point.parentfield == parentfield)
			& (Upper(loading_point.location_type) == "LOADING POINT")
		)
		.orderby(route_step.idx, order=Order.asc)
		.limit(1)
	)


def get_last_position_query(trip, leg):
	location_update = frappe.qb.DocType("Vehicle Trip Location Update")
	position = Concat(
		DateFormat(location_update.timestamp, "%d-%m-%Y %l:%i"), " - ", location_update.location
	)
	return (
		frappe.qb.from_(location_update)
		.select(position)
		.where(
			(location_update.parenttype == "Vehicle Trip")
			& (location_update.parent == trip.name)
			& (location_update.parentfield == f"{leg}_location_update")
		)
		.orderby(location_update.timestamp, order=Order.desc)
		.limit(1)
	)
