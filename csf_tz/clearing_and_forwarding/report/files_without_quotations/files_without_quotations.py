# Copyright (c) 2013, Bravo Logisitcs and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "reference",
			"label": _("Reference"),
			"fieldtype": "Link",
			"options": "Files",
			"width": 150,
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 250,
		},
		{"fieldname": "documents_received_date", "label": _("Date"), "fieldtype": "Date", "width": 150},
	]

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	files = frappe.qb.DocType("Files")
	data = (
		frappe.qb.from_(files)
		.select(files.name.as_("reference"), files.customer, files.documents_received_date)
		.where(files.quotation.isnull())
		.where(files.documents_received_date[filters.from_date : filters.to_date])
		.run(as_dict=True)
	)

	return columns, data
