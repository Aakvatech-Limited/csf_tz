from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
import ast
from datetime import datetime

def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "creation_document_no",
			"label": _("Creation Document No"),
			"fieldtype": "Dynamic Link",
			"width": 100
		},
		{
			"fieldname": "shipping_line",
			"label": _("Shipping Line"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "export_reference",
			"label": _("Export Reference"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "booking_number",
			"label": _("Booking Number"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "container_no",
			"label": _("Container No"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "container_type",
			"label": _("Container Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "seal_number",
			"label": _("Seal Number"),
			"fieldtype": "Data",
			"width": 100
		},
	]
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	container = frappe.qb.DocType("Container")
	query = (
		frappe.qb.from_(container)
		.select(
			container.creation_document_no,
			container.shipping_line,
			container.export_reference,
			container.booking_number,
			container.container_no,
			container.container_type,
			container.seal_number,
		)
		.where(container.export_reference.isnull())
	)
	if filters.shipping_line:
		query = query.where(container.shipping_line == filters.shipping_line)

	data = query.run(as_dict=True)

	return columns, data

