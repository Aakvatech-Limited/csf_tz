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
