import frappe
from frappe.query_builder import Case, Order


def get_case_by_joined_table(values_by_table):
	"""CASE returning the value paired with the first left-joined table that has a row."""
	case = Case()
	for table, value in values_by_table:
		case = case.when(table.name.isnotnull(), value)
	return case


def get_trip_location_query(trip, leg):
	"""Subquery for the location of the earliest location update of the `leg` of `trip`."""
	location_update = frappe.qb.DocType("Vehicle Trip Location Update")
	return (
		frappe.qb.from_(location_update)
		.select(location_update.location)
		.where(
			(location_update.parent == trip.name)
			& (location_update.parenttype == "Vehicle Trip")
			& (location_update.parentfield == f"{leg}_location_update")
		)
		.orderby(location_update.timestamp, order=Order.asc)
		.limit(1)
	)


def get_offloaded_trips_query(parentfield, offloading_dates):
	"""Query for the Vehicle Trips with a route step in `parentfield` offloaded on one of `offloading_dates`."""
	route_steps = frappe.qb.DocType("Route Steps Table")
	return (
		frappe.qb.from_(route_steps)
		.select(route_steps.parent)
		.where(
			(route_steps.parenttype == "Vehicle Trip")
			& (route_steps.parentfield == parentfield)
			& route_steps.offloading_date.isin(offloading_dates)
		)
	)
