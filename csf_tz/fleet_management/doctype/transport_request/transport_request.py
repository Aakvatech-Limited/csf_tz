# -*- coding: utf-8 -*-
# Copyright (c) 2015, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import time
import datetime
from frappe.model.document import Document
from frappe import _
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now

class TransportRequest(Document):
	def before_save(self):
		#For assignment status
		if not self.assign_transport:
			self.set('assignment_status', 'Waiting Assignment')
		elif self.cargo_type == 'Container':
			assigned_containers = []
			for row in self.assign_transport:
				assigned_containers.append(row.container_number)
				
			for row in self.cargo:
				if row.container_number not in assigned_containers:
					self.set('assignment_status', 'Partially Assigned')
				else:
					self.set('assignment_status', 'Fully Assigned')
		elif self.cargo_type == 'Loose Cargo':
			total_assigned = 0;
			for row in self.assign_transport:
				total_assigned = total_assigned + row.get('amount', 0)
				
			if self.amount > total_assigned:
				self.set('assignment_status', 'Partially Assigned')
			else:
				self.set('assignment_status', 'Fully Assigned')
	
	def get_all_children(self, parenttype=None):
		#If reference doctype is set
		if self.get('reference_docname'):
			return self.get('assign_transport')
		else:
			"""Returns all children documents from **Table** type field in a list."""
			ret = []
			
			for df in self.meta.get("fields", {"fieldtype": "Table"}):
				if parenttype:
					if df.options==parenttype:
						return self.get(df.fieldname)
				value = self.get(df.fieldname)
				if isinstance(value, list):
					ret.extend(value)
			return ret
		
		
	def update_children(self):
		#update child tables
		#If reference doctype is set
		if self.get('reference_docname'):
			self.update_child_table('assign_transport')
		else:
			for df in self.meta.get_table_fields():
				self.update_child_table(df.fieldname, df)

	
	'''def set_parent_in_children(self):
		"""Updates `parent` and `parenttype` property in all children."""
		#If reference doctype is set
		if self.get('reference_docname'):
			for d in self.get_all_children():
				d.parent = self.get('reference_docname')
				d.parenttype = self.get('reference_doctype')
				if self.get('reference_doctype') == "Import":
					d.parentfield = "assign_transport"
		else:
			for d in self.get_all_children():
				d.parent = self.name
				d.parenttype = self.doctype'''
	
	
	#Custom load method for loading child tables data from imports and exports request
	def load_from_db(self):
		"""Load document and children from database and create properties
		from fields"""
		if not getattr(self, "_metaclass", False) and self.meta.issingle:
			single_doc = frappe.db.get_singles_dict(self.doctype)
			if not single_doc:
				single_doc = frappe.new_doc(self.doctype).as_dict()
				single_doc["name"] = self.doctype
				del single_doc["__islocal"]

			super(Document, self).__init__(single_doc)
			self.init_valid_columns()
			self._fix_numeric_types()

		else:
			d = frappe.db.get_value(self.doctype, self.name, "*", as_dict=1)
			if not d:
				frappe.throw(_("{0} {1} not found").format(_(self.doctype), self.name), frappe.DoesNotExistError)

			super(Document, self).__init__(d)

		if self.name=="DocType" and self.doctype=="DocType":
			from frappe.model.meta import doctype_table_fields
			table_fields = doctype_table_fields
		else:
			table_fields = self.meta.get_table_fields()
		
		#
		# For table fields load from request origin(if there is) else load normal
		# Also add back compatibiilty for when transport assignements were being loaded from import
		#
		for df in table_fields:			
			if d.reference_doctype and d.reference_docname:
				#Fieldname depending on if it's Export or Import
				if d.reference_doctype == "Import" and df.fieldname == "cargo":
					fieldname = "cargo_information"
				elif d.reference_doctype == "Import" and df.fieldname == "assign_transport":
					fieldname = "assign_transport"
				
				if df.fieldname == "assign_transport" and self.get('version') == 2:
					children = frappe.db.get_values(df.options,
					{"parent": self.name, "parenttype": self.doctype, "parentfield": 'assign_transport'},
					"*", as_dict=True, order_by="idx asc")
				else:
					children = frappe.db.get_values(df.options,
					{"parent": d.reference_docname, "parenttype": d.reference_doctype, "parentfield": fieldname},
					"*", as_dict=True, order_by="idx asc")
				
				
				if children:
					self.set(df.fieldname, children)
				else:
					self.set(df.fieldname, [])
			else:
				children = frappe.db.get_values(df.options,
					{"parent": self.name, "parenttype": self.doctype, "parentfield": df.fieldname},
					"*", as_dict=True, order_by="idx asc")
				if children:
					self.set(df.fieldname, children)
				else:
					self.set(df.fieldname, [])
		
		# sometimes __setup__ can depend on child values, hence calling again at the end
		if hasattr(self, "__setup__"):
			self.__setup__()


@frappe.whitelist(allow_guest=True)
def transport_request_scheduler():
	#Create requests for imports less than 10 days to eta
	import_doctype = frappe.qb.DocType("Import")
	imports_past_eta = (
		frappe.qb.from_(import_doctype)
		.select(import_doctype.name, import_doctype.eta, import_doctype.reference_file_number)
		.where(
			((import_doctype.status != "Closed") | import_doctype.status.isnull())
			& (import_doctype.eta < Now() - Interval(days=10))
		)
	).run(as_dict=True)
	for row in imports_past_eta:
		create_transport_request(reference_doctype="Import", reference_docname=row.name, file_number=row.reference_file_number)
	

	
@frappe.whitelist(allow_guest=True)
def create_transport_request(**args):
	args = frappe._dict(args)
	
	existing_transport_request = frappe.db.get_value("Transport Request", 
		{"file_number": args.file_number})
	
	#Timestamp
	ts = time.time()
	timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
	
	if not existing_transport_request:
		request = frappe.new_doc("Transport Request")
		request.update({
			"reference_doctype":args.reference_doctype,
			"reference_docname": args.reference_docname,
			"file_number": args.file_number,
			"request_received": args.request_received,
			"customer": args.customer,
			"consignee": args.consignee,
			"shipper": args.shipper,
			"cargo_location_country": args.cargo_location_country,
			"cargo_location_city": args.cargo_location_city,
			"cargo_destination_country": args.cargo_destination_country,
			"cargo_destination_city": args.cargo_destination_city,
			"transport_type": args.transport_type,
			"version": 2
		})
		request.insert(ignore_permissions=True)
		return request.name
	else:
		return existing_transport_request

@frappe.whitelist(allow_guest=True)		
def assign_vehicle(**args):
	args = frappe._dict(args)
	
	#Change cargo status to assigned (1)
	#doc = frappe.get_doc("Cargo Details", args.cargo_docname)
	#doc.db_set("transport_status", "0", False)
	#doc.db_set("idx", args.cargo_idx, False)
	
	#Add/Update assigned transport details
	existing_transport_details = frappe.db.get_value("Transport Assignment", 
		{"cargo": args.cargo_docname})
		
	if existing_transport_details:
		#Update the transport details
		doc = frappe.get_doc("Transport Assignment", existing_transport_details)
		doc.assigned_vehicle = args.assigned_vehicle
		doc.assigned_trailer = args.assigned_trailer
		doc.assigned_driver = args.assigned_driver
		doc.cargo = args.cargo_docname
		doc.amount = args.amount
		doc.expected_loading_date = args.expected_loading_date
		doc.container_number = args.container_number
		doc.units = args.units
		doc.transporter_type = args.transporter_type
		doc.sub_contractor = args.sub_contractor
		doc.vehicle_plate_number = args.vehicle_plate_number
		doc.trailer_plate_number = args.trailer_plate_number
		doc.driver_name = args.driver_name
		doc.passport_number = args.passport_number
		doc.route = args.route
		doc.idx = args.assigned_idx
		doc.save()
	else:
		request = frappe.new_doc("Transport Assignment")
		request.update({
			"cargo": args.cargo_docname,
			"amount": args.amount,
			"expected_loading_date": args.expected_loading_date,
			"container_number": args.container_number,
			"units": args.units,
			"transporter_type": args.transporter_type,
			"sub_contractor": args.sub_contractor,
			"vehicle_plate_number": args.vehicle_plate_number,
			"trailer_plate_number": args.trailer_plate_number,
			"driver_name": args.driver_name,
			"passport_number": args.passport_number,
			"route": args.route,
			"parent": args.reference_docname,
			"parenttype": args.reference_doctype,
			"parentfield": "assign_transport",
			"assigned_vehicle": args.assigned_vehicle,
			"assigned_trailer": args.assigned_trailer,
			"assigned_driver": args.assigned_driver,
			"idx": args.assigned_idx
		})
		request.insert(ignore_permissions=True)
	
	#Edit vehicle status
	
	'''vehicle = frappe.get_doc("Vehicle", args.assigned_vehicle)
	if vehicle.status == 'Available':
		vehicle.status = "Booked"
		vehicle.save()'''
	return "success"
	
