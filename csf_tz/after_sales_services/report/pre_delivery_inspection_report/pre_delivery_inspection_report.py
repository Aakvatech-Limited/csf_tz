# Copyright (c) 2013, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
import ast
import datetime

def execute(filters=None):
	columns, data = [], []
	
	columns = [
		{
			"fieldname": "reference",
			"label": _("Pre Delivery Inspection Reference"),
			"fieldtype": "Link",
			"options": "Pre Delivery Inspection",
			"width": 100
		},
		{
			"fieldname": "report_date",
			"label": _("Done On"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "inspection_type",
			"label": _("Inspection Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "item_code",
			"label": _("Item code"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "item_serial_no",
			"label": _("Serial no"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "inspected_by",
			"label": _("Inspected By"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "verified_by",
			"label": _("Verified By"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Text",
			"width": 200
		}
	]
	
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))
		
	pre_delivery_inspection = frappe.qb.DocType("Pre Delivery Inspection")
	sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
	query = (
		frappe.qb.from_(pre_delivery_inspection)
		.left_join(sales_invoice_item)
		.on(pre_delivery_inspection.sales_invoice == sales_invoice_item.parent)
		.select(
			pre_delivery_inspection.name.as_("reference"),
			pre_delivery_inspection.report_date,
			pre_delivery_inspection.customer,
			pre_delivery_inspection.inspection_type,
			pre_delivery_inspection.item_code,
			pre_delivery_inspection.item_serial_no,
			pre_delivery_inspection.inspected_by,
			pre_delivery_inspection.verified_by,
			pre_delivery_inspection.reference_name,
			pre_delivery_inspection.remarks,
			sales_invoice_item.warehouse,
		)
		.where(pre_delivery_inspection.docstatus != 2)
		.where(pre_delivery_inspection.report_date[filters.from_date:filters.to_date])
	)

	if filters.branch:
		query = query.where(sales_invoice_item.warehouse == filters.branch)

	data = query.run(as_dict=1)
						 
	return columns, data