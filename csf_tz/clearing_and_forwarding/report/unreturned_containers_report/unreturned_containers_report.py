# Copyright (c) 2013, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "import_no",
			"label": _("Import No"),
			"fieldtype": "Link",
			"options": "Import",
			"width": 150

		},
		{
			"fieldname": "reference_file_number",
			"label": _("Reference File Number"),
			"fieldtype": "Link",
			"options" :"Files",
			"width": 200
		},
		{
			"fieldname": "bl_number",
			"label": _("B/L Number"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "shipping_line",
			"label": _("Shipping Line"),
			"fieldtype": "Link",
			"options": "Shipping Line",
			"width": 200
		},
		{
			"fieldname": "container_owner",
			"label": _("Container Owner"),
			"fieldtype": "Select",
			"options": "SOC (Shipper Owned Container)\nShipping Line Container\nBravo Container\nRental",
			"width": 200
		},
		{
			"fieldname": "container_no",
			"label": _("Container No"),
			"fieldtype": "Data",
			"width": 150
		},

		{
			"fieldname": "container_return_date",
			"label": _("Container Return Date"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "demurrage_start_date",
			"label": _("Demurrage Start Date"),
			"fieldtype": "Date",
			"width": 150
		}

	]

	import_doc = frappe.qb.DocType("Import")
	closing_information = frappe.qb.DocType("Container File Closing Information")
	query = (
		frappe.qb.from_(import_doc)
		.left_join(closing_information).on(import_doc.name == closing_information.parent)
		.select(
			import_doc.name.as_("import_no"),
			import_doc.reference_file_number,
			import_doc.bl_number,
			import_doc.shipping_line,
			import_doc.container_owner,
			closing_information.container_no,
			closing_information.container_return_date,
			import_doc.demurrage_start_date,
		)
	)

	if filters.from_date:
		query = query.where(import_doc.demurrage_start_date >= filters.from_date)

	if filters.container_owner:
		query = query.where(import_doc.container_owner == filters.container_owner)

	if filters.shipping_line:
		query = query.where(import_doc.shipping_line == filters.shipping_line)

	data = query.run(as_dict=True)
	return columns, data
