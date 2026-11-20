# Copyright (c) 2015, Bravo Logistics and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class TripRoute(Document):
	def validate(self):
		self.before_save()

	def before_save(self):
		for d in self.get("trip_steps"):
			if d.idx == 1 and d.location_type != "Loading Point":
				frappe.throw("Set 1st location type to LOADING POINT")
				break
			if d.idx == len(self.get("trip_steps")) and d.location_type != "Offloading Point":
				frappe.throw("Set last location type to OFFLOADING POINT")
				break
