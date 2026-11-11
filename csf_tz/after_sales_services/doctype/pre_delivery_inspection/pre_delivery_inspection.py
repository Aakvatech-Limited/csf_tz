# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _, msgprint, throw
import json

class PreDeliveryInspection(Document):
	def onload(self):
		""" Load delivery Note link """
		dashboard_links_html = self.load_delivery_note()
		self.set_onload("dashboard_links_html", {"display": dashboard_links_html})

	def load_delivery_note(self):
		delivery_note_links = []
		delivery_note_item = frappe.qb.DocType("Delivery Note Item")
		installation_note = frappe.qb.DocType("Installation Note")
		delivery_note_links = (
			frappe.qb.from_(delivery_note_item)
			.left_join(installation_note)
			.on(delivery_note_item.parent == installation_note.delivery_note)
			.select(
				delivery_note_item.item_code,
				delivery_note_item.parent,
				delivery_note_item.serial_no,
				delivery_note_item.against_sales_invoice,
				installation_note.name.as_("installation"),
			)
			.where(delivery_note_item.against_sales_invoice == self.reference_name)
			.where(delivery_note_item.item_code == self.item_code)
			.where(delivery_note_item.serial_no == self.item_serial_no)
		).run(as_dict=True)
		self.set_onload("delivery_note_links", delivery_note_links)
		#frappe.msgprint(_(json.dumps(delivery_note_links)))

		return frappe.render_template("templates/pre_delivery_links.html", {"delivery_note_links": delivery_note_links})
