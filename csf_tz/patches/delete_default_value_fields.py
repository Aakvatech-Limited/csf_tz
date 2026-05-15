from __future__ import unicode_literals

import frappe


def execute():
	defkeys = ["year_start_date", "year_end_date"]
	for defkey in defkeys:
		if frappe.db.exists("DefaultValue", {"defkey": defkey}):
			frappe.db.delete("DefaultValue", {"defkey": defkey})
