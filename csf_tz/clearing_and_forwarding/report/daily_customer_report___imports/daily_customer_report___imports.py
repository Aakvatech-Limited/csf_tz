# Copyright (c) 2013, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, getdate, cstr
from frappe import _
from frappe.query_builder import Case, Field
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
			"options": "Import",
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
			"fieldname": "customer_ref",
			"label": _("Customer Ref"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "consignee",
			"label": _("Consignee"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 100
		},
		{
			"fieldname": "destination",
			"label": _("Destination"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "doc_rec_date",
			"label": _("Docs Received Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "cargo",
			"label": _("Cargo"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "container_number",
			"label": _("Container No"),
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
			"label": _("Weight"),
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "eta",
			"label": _("ETA"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "ata",
			"label": _("ATA"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "discharge_date",
			"label": _("Discharge Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "assigned_transport",
			"label": _("Assigned Transport"),
			"fieldtype": "Link",
			"options": "Transport Assignment",
			"width": 100
		},
		{
			"fieldname": "trip_reference",
			"label": _("Trip Ref"),
			"fieldtype": "Link",
			"options": "Vehicle Trip",
			"width": 100
		},
		{
			"fieldname": "truck_trailer_no",
			"label": _("Truck/Trailer No"),
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "driver_name",
			"label": _("Driver Name"),
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "licence",
			"label": _("Licence"),
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "contacts",
			"label": _("Contacts"),
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "loading_date",
			"label": _("Loading Date"),
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
			"fieldname": "border1_name",
			"label": _("1st Border"),
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "border1_arrival_date",
			"label": _("1st Border Arrival Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "border1_dispatch_date",
			"label": _("1st Border Dispatch Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "border2_name",
			"label": _("2nd Border"),
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "border2_arrival_date",
			"label": _("2nd Border Arrival Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "border2_dispatch_date",
			"label": _("2nd Border Dispatch Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "arrival_destination",
			"label": _("Arrival Destination"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "cargo_offloaded",
			"label": _("Cargo Offloaded"),
			"fieldtype": "Date",
			"width": 100
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
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))
		
	import_doc = frappe.qb.DocType("Import")
	order_by = Field("file_number")
	if filters.customer:
		order_by &= (import_doc.customer == filters.customer)
	
	
	#where_filter.update({"where": where})
	
	'''data = frappe.db.sql(SELECT * FROM
					(SELECT
						tabImport.name AS file_number,
						tabImport.customer,
						CASE
							WHEN tabImport.house_bill_of_lading IS NULL OR tabImport.house_bill_of_lading = '' THEN  tabImport.bl_number 
						ELSE tabImport.house_bill_of_lading
						END AS customer_ref,
						tabImport.consignee,
						tabImport.cargo_destination_city AS destination,
						tabImport.documents_received_date AS doc_rec_date,
						tabImport.cargo_description AS cargo,
						`tabCargo Details`.container_number,
						CASE
							WHEN `tabCargo Details`.container_size IN ('40 FT GP', '40 OT', '40RF', '40 FT Heavy') THEN '40'
							WHEN `tabCargo Details`.container_size IN ('20 FT GP', '20 OT', '20RF') THEN '20'
						END AS container_size,
						`tabCargo Details`.gross_weight AS weight,
						tabImport.eta,
						tabImport.ata,
						tabImport.discharge AS discharge_date,
						CONCAT(`tabTransport Assignment`.vehicle_plate_number, "/", `tabTransport Assignment`.vehicle_plate_number) AS truck_trailer_no,
						`tabTransport Assignment`.driver_name,
						tabImport.loading_date,
						loading_point.departure_date AS dispatch_date,
						border1.arrival_date AS border_arrival_date,
						border1.departure_date AS border_dispatch_date,
						offloading_point.arrival_date AS arrival_destination,
						offloading_point.offloading_date AS cargo_offloaded,
						(SELECT `tabVehicle Trip Location Update`.location FROM `tabVehicle Trip Location Update` WHERE parent = `tabVehicle Trip`.name
							AND parenttype = 'Vehicle Trip' AND parentfield = 'main_location_update' ORDER BY `tabVehicle Trip Location Update`.timestamp DESC LIMIT 1) AS vehicle_position,
						CASE
							WHEN `tabVehicle Trip`.name IS NOT NULL THEN (SELECT `tabReporting Status Table`.status FROM `tabReporting Status Table` \
								WHERE `tabReporting Status Table`.parenttype = 'Vehicle Trip' AND `tabReporting Status Table`.parent = `tabVehicle Trip`.name \
								ORDER BY `tabReporting Status Table`.datetime DESC LIMIT 1)
							ELSE (SELECT `tabReporting Status Table`.status FROM `tabReporting Status Table` \
								WHERE `tabReporting Status Table`.parenttype = 'Import' AND `tabReporting Status Table`.parent = `tabImport`.name \
								ORDER BY `tabReporting Status Table`.datetime DESC LIMIT 1)
						END AS remarks
					FROM
						`tabCargo Details`
					LEFT JOIN 
						tabImport ON tabImport.name = `tabCargo Details`.parent
					LEFT JOIN
						`tabTransport Assignment` ON `tabTransport Assignment`.container_number = `tabCargo Details`.container_number
					LEFT JOIN
						`tabVehicle Trip` ON `tabVehicle Trip`.reference_docname = `tabTransport Assignment`.name 
					LEFT JOIN
						 `tabRoute Steps Table` AS loading_point \
						 ON loading_point.name = (SELECT `tabRoute Steps Table`.name FROM `tabRoute Steps Table` WHERE \
						 `tabRoute Steps Table`.parent = `tabVehicle Trip`.name AND UPPER(location_type) = 'LOADING POINT' and loading_point.parentfield = 'main_route_steps' LIMIT 1)
					LEFT JOIN
						`tabRoute Steps Table` AS border1 \
						 ON border1.name = (SELECT `tabRoute Steps Table`.name FROM `tabRoute Steps Table` WHERE \
						 `tabRoute Steps Table`.parent = `tabVehicle Trip`.name AND UPPER(location_type) = 'BORDER' and border1.parentfield = 'main_route_steps' LIMIT 1)
					LEFT JOIN
						`tabRoute Steps Table` AS offloading_point \
						 ON offloading_point.name = (SELECT `tabRoute Steps Table`.name FROM `tabRoute Steps Table` WHERE \
						 `tabRoute Steps Table`.parent = `tabVehicle Trip`.name AND UPPER(location_type) = 'OFFLOADING POINT' and `tabRoute Steps Table`.parentfield = 'main_route_steps' LIMIT 1)
					WHERE
						`tabCargo Details`.parenttype = 'Import' AND tabImport.status <> 'Closed' AND \
						`tabVehicle Trip`.name IS NULL OR `tabVehicle Trip`.status = 'En Route' OR offloading_point.offloading_date IN (%(today)s, %(yesterday)s, %(day_before)s)
				 + where + 
				UNION ALL
					SELECT
						tabImport.name AS file_number,
						tabImport.customer,
						CASE
							WHEN tabImport.house_bill_of_lading IS NULL OR tabImport.house_bill_of_lading = '' THEN  tabImport.bl_number 
						ELSE tabImport.house_bill_of_lading
						END AS customer_ref,
						tabImport.consignee,
						tabImport.cargo_destination_city AS destination,
						tabImport.documents_received_date AS doc_rec_date,
						tabImport.cargo_description AS cargo,
						`tabCargo Details`.container_number,
						CASE
							WHEN `tabCargo Details`.container_size IN ('40 FT GP', '40 OT', '40RF', '40 FT Heavy') THEN '40'
							WHEN `tabCargo Details`.container_size IN ('20 FT GP', '20 OT', '20RF') THEN '20'
						END AS container_size,
						`tabCargo Details`.gross_weight AS weight,
						tabImport.eta,
						tabImport.ata,
						tabImport.discharge AS discharge_date,
						CONCAT(`tabTransport Assignment`.vehicle_plate_number, "/", `tabTransport Assignment`.vehicle_plate_number) AS truck_trailer_no,
						`tabTransport Assignment`.driver_name,
						tabImport.loading_date,
						loading_point.departure_date AS dispatch_date,
						border1.arrival_date AS border_arrival_date,
						border1.departure_date AS border_dispatch_date,
						offloading_point.arrival_date AS arrival_destination,
						offloading_point.offloading_date AS cargo_offloaded,
						(SELECT `tabVehicle Trip Location Update`.location FROM `tabVehicle Trip Location Update` WHERE parent = `tabVehicle Trip`.name
							AND parenttype = 'Vehicle Trip' AND parentfield = 'return_location_update' ORDER BY `tabVehicle Trip Location Update`.timestamp DESC LIMIT 1) AS vehicle_position,
						CASE
							WHEN `tabVehicle Trip`.name IS NOT NULL THEN (SELECT `tabReporting Status Table`.status FROM `tabReporting Status Table` \
								WHERE `tabReporting Status Table`.parenttype = 'Vehicle Trip' AND `tabReporting Status Table`.parent = `tabVehicle Trip`.name \
								ORDER BY `tabReporting Status Table`.datetime DESC LIMIT 1)
							ELSE (SELECT `tabReporting Status Table`.status FROM `tabReporting Status Table` \
								WHERE `tabReporting Status Table`.parenttype = 'Import' AND `tabReporting Status Table`.parent = `tabImport`.name \
								ORDER BY `tabReporting Status Table`.datetime DESC LIMIT 1)
						END AS remarks
					FROM
						`tabCargo Details`
					LEFT JOIN 
						tabImport ON tabImport.name = `tabCargo Details`.parent
					LEFT JOIN
						`tabTransport Assignment` ON `tabTransport Assignment`.container_number = `tabCargo Details`.container_number
					LEFT JOIN
						`tabVehicle Trip` ON `tabVehicle Trip`.return_reference_docname = `tabTransport Assignment`.name
					LEFT JOIN
						 `tabRoute Steps Table` AS loading_point \
						 ON loading_point.name = (SELECT `tabRoute Steps Table`.name FROM `tabRoute Steps Table` WHERE \
						 `tabRoute Steps Table`.parent = `tabVehicle Trip`.name AND UPPER(location_type) = 'LOADING POINT' and loading_point.parentfield = 'return_route_steps' LIMIT 1)
					LEFT JOIN
						`tabRoute Steps Table` AS border1 \
						 ON border1.name = (SELECT `tabRoute Steps Table`.name FROM `tabRoute Steps Table` WHERE \
						 `tabRoute Steps Table`.parent = `tabVehicle Trip`.name AND UPPER(location_type) = 'BORDER' and border1.parentfield = 'return_route_steps' LIMIT 1)
					LEFT JOIN
						`tabRoute Steps Table` AS offloading_point \
						 ON offloading_point.name = (SELECT `tabRoute Steps Table`.name FROM `tabRoute Steps Table` WHERE \
						 `tabRoute Steps Table`.parent = `tabVehicle Trip`.name AND UPPER(location_type) = 'OFFLOADING POINT' and `tabRoute Steps Table`.parentfield = 'return_route_steps' LIMIT 1)
					WHERE
						`tabCargo Details`.parenttype = 'Import' AND tabImport.name IS NOT NULL AND  tabImport.status <> 'Closed' AND \
						`tabVehicle Trip`.name IS NULL OR `tabVehicle Trip`.status = 'En Route - Returning' OR offloading_point.offloading_date IN (%(today)s, %(yesterday)s, %(day_before)s)
					+ where + 
				) a, where_filter, as_dict=1)'''
				
				
	cargo = frappe.qb.DocType("Cargo Details")
	data = (
		frappe.qb.from_(cargo)
		.left_join(import_doc).on(import_doc.name == cargo.parent)
		.select(
			import_doc.name.as_("file_number"),
			import_doc.customer,
			Case()
			.when(import_doc.house_bill_of_lading.isnull() | (import_doc.house_bill_of_lading == ''), import_doc.bl_number)
			.else_(import_doc.house_bill_of_lading)
			.as_("customer_ref"),
			import_doc.consignee,
			import_doc.cargo_destination_city.as_("destination"),
			import_doc.documents_received_date.as_("doc_rec_date"),
			import_doc.cargo_description.as_("cargo"),
			cargo.name.as_("cargo_reference"),
			cargo.container_number,
			Case()
			.when(cargo.container_size.isin(['40 FT GP', '40 OT', '40RF', '40 FT Heavy']), '40')
			.when(cargo.container_size.isin(['20 FT GP', '20 OT', '20RF']), '20')
			.as_("container_size"),
			cargo.gross_weight.as_("weight"),
			import_doc.eta,
			import_doc.ata,
			import_doc.discharge.as_("discharge_date"),
			import_doc.loading_date,
			get_latest_reporting_status_query(import_doc.name, "Import").as_("remarks"),
		)
		.where(cargo.parenttype == 'Import')
		.where(import_doc.status != 'Closed')
		.orderby(order_by)
		.run(as_dict=True)
	)
				
	if data:
		for importd in data:
			assigned_transport = frappe.db.get_value('Transport Assignment', {"cargo": importd.cargo_reference})
			if assigned_transport and assigned_transport != '':
				assignment_details = frappe.get_doc('Transport Assignment', assigned_transport)
				importd.update({
					"truck_trailer_no": str(assignment_details.vehicle_plate_number) + '/' + str(assignment_details.trailer_plate_number),
					"driver_name": str(assignment_details.driver_name),
					"licence": assignment_details.driver_licence,
					"assigned_transport": assigned_transport
				})
				is_main_trip = frappe.db.get_value("Vehicle Trip", 
												{"reference_doctype": "Transport Assignment", "reference_docname": importd.assigned_transport})
				is_return_trip = frappe.db.get_value("Vehicle Trip", 
												{"return_reference_doctype": "Transport Assignment", "return_reference_docname": importd.assigned_transport})
												
				if is_main_trip:
					main_trip = frappe.get_doc("Vehicle Trip", is_main_trip)
					border1, border2 = False, False
					importd.update({
						"trip_reference": main_trip.name,
						"licence": main_trip.driving_licence_no,
						"contacts": main_trip.phone_number
					})					
					for location in main_trip.main_route_steps:
						#Vehicle location update
						if main_trip.main_location_update:
							importd.update({
								"vehicle_position": main_trip.main_location_update[-1].location
							})
						
						#Remarks update
						if main_trip.main_reporting_status:
							importd.update({
								"remarks": main_trip.main_reporting_status[-1].status
							})
						
						if location.location_type and location.location_type.upper() == 'LOADING POINT':
							importd.update({
								'loading_date': location.loading_date,
								"dispatch_date": location.departure_date
							})
						elif location.location_type and location.location_type.upper() == 'OFFLOADING POINT':
							importd.update({
								"arrival_destination": location.arrival_date,
								"cargo_offloaded": location.offloading_date
							})
						elif location.location_type and location.location_type.upper() == 'BORDER' and not border1:
							importd.update({
								"border1_name": location.location,
								"border1_arrival_date": location.arrival_date,
								"border1_dispatch_date": location.departure_date
							})
							border1 = True
						elif location.location_type and location.location_type.upper() == 'BORDER' and not border2:
							importd.update({
								"border2_name": location.location,
								"border2_arrival_date": location.arrival_date,
								"border2_dispatch_date": location.departure_date
							})
							border2 = True
				elif is_return_trip:
					return_trip = frappe.get_doc("Vehicle Trip", is_return_trip)
					border1, border2 = False, False
					importd.update({
						"trip_reference": return_trip.name,
						"licence": return_trip.driving_licence_no,
						"contacts": return_trip.phone_number
					})	
					for location in return_trip.return_route_steps:
						#Vehicle location update
						if return_trip.return_location_update:
							importd.update({
								"vehicle_position": return_trip.return_location_update[-1].location
							})
						
						#Remarks update
						if return_trip.return_reporting_status:
							importd.update({
								"remarks": return_trip.return_reporting_status[-1].status
							})
						
						if location.location_type and location.location_type.upper() == 'LOADING POINT':
							importd.update({
								'loading_date': location.loading_date,
								"dispatch_date": location.departure_date
							})
						elif location.location_type and location.location_type.upper() == 'OFFLOADING POINT':
							importd.update({
								"arrival_destination": location.arrival_date,
								"cargo_offloaded": location.offloading_date
							})
						elif location.location_type and location.location_type.upper() == 'BORDER' and not border1:
							importd.update({
								"border1_name": location.location,
								"border1_arrival_date": location.arrival_date,
								"border1_dispatch_date": location.departure_date
							})
							border1 = True
						elif location.location_type and location.location_type.upper() == 'BORDER' and not border2:
							importd.update({
								"border2_name": location.location,
								"border2_arrival_date": location.arrival_date,
								"border2_dispatch_date": location.departure_date
							})
							border2 = True
							
		#Remove imports offloaded more than two days ago
		for i in xrange(len(data) - 1, -1, -1):
			if data[i].cargo_offloaded and data[i].cargo_offloaded not in [today, yesterday, day_before]:
				del data[i]
				
	
	return columns, data
