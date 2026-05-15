# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class BinSetup(Document):
	def validate(self):
		self.before_save()

	def before_save(self):
		for d in self.bin_table:
			if d.new_label:
				bin_no = frappe.db.get_value(
					"Bin",
					{
						"item_code": d.item_code,
						"warehouse": d.warehouse,
					},
					"name",
				)
				if bin_no:
					doc = frappe.get_doc("Bin", bin_no)
					doc.bin_label = d.new_label
					doc.save()
		self.bin_table = []
