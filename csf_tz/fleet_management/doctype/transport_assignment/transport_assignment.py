# -*- coding: utf-8 -*-
# Copyright (c) 2015, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.query_builder import Order

class TransportAssignment(Document):
	def onload(self):
		if self.transporter_type == 'Bravo':
			vehicle_trip = frappe.qb.DocType("Vehicle Trip")
			previous_trips = (
				frappe.qb.from_(vehicle_trip)
				.select(vehicle_trip.name, vehicle_trip.hidden_status)
				.where(
					(vehicle_trip.vehicle == self.assigned_vehicle)
					& (vehicle_trip.transporter_type == "Bravo")
				)
				.orderby(vehicle_trip.creation, order=Order.desc)
				.limit(20)
			).run(as_dict=True)
			if previous_trips:
				self.set("vehicle_status", previous_trips[0].hidden_status)
				self.set("vehicle_trip", previous_trips[0].name)

@frappe.whitelist(allow_guest=True)
def change_assignment_status(**args):
	args = frappe._dict(args)
	doc = frappe.get_doc("Transport Assignment", args.assignment_docname)
	doc.db_set('status', 'Not Processed')
