# Copyright (c) 2013, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
from frappe.query_builder import Case, Order
from frappe.query_builder.functions import Concat
from csf_tz.fleet_management.trip_queries import get_offloaded_trips_query
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
	
	data = get_vehicle_status_query().run(as_dict=True)
	for row in data:
		if row.next_assigned_parenttype and row.next_assigned_parent:
			next_assigned = None
			if row.next_assigned_parenttype == 'Import':
				next_assigned = frappe.get_doc('Import', row.next_assigned_parent).customer
			elif row.next_assigned_parenttype == 'Transport Request':
				next_assigned = frappe.get_doc('Transport Request', row.next_assigned_parent).customer
			row.update({"next_cargo_allocation": next_assigned})
				
	return columns, data


def get_vehicle_status_query():
	vehicle = frappe.qb.DocType("Vehicle")
	trailer = frappe.qb.DocType("Trailer")
	employee = frappe.qb.DocType("Employee")
	transport_assignment = frappe.qb.DocType("Transport Assignment")
	pending_assignment = frappe.qb.DocType("Transport Assignment").as_("pending_assignment")
	next_assignment = (
		frappe.qb.from_(pending_assignment)
		.select(pending_assignment.name)
		.where(
			(pending_assignment.assigned_vehicle == vehicle.name)
			& (pending_assignment.status == "Not Processed")
		)
		.orderby(pending_assignment.expected_loading_date, order=Order.asc)
		.limit(1)
	)
	registration_number = (
		Case()
		.when(trailer.number_plate, Concat(vehicle.number_plate, "/", trailer.number_plate))
		.else_(vehicle.number_plate)
	)
	return (
		frappe.qb.from_(vehicle)
		.left_join(trailer)
		.on(trailer.name == vehicle.default_trailer)
		.left_join(employee)
		.on(employee.name == vehicle.driver)
		.left_join(transport_assignment)
		.on(transport_assignment.name == next_assignment)
		.select(
			vehicle.fleet_number.as_("fleet_no"),
			registration_number.as_("reg_no"),
			vehicle.name,
			employee.employee_name.as_("driver_name"),
			employee.cell_number.as_("contact"),
			transport_assignment.parenttype.as_("next_assigned_parenttype"),
			transport_assignment.parent.as_("next_assigned_parent"),
		)
	)


def get_trip_info(data):
	if data:
		for vehicle in data:
			main_trip = frappe.db.get_value('Vehcile Trip', {"vehicle": vehicle.name, "status": "En Route"})
			return_trip = frappe.db.get_value('Vehcile Trip', {"vehicle": vehicle.name, "status": "En Route - Returning"})
			main_offloaded = get_offloaded_trip("main_route_steps", [today, yesterday, day_before])
			return_offloaded = get_offloaded_trip("return_route_steps", [today, yesterday, day_before])


def get_offloaded_trip(parentfield, offloading_dates):
	return get_offloaded_trips_query(parentfield, offloading_dates).limit(1).run()
