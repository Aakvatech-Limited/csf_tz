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
			"label": _("Installation Note"),
			"fieldtype": "Link",
			"options": "Installation Note",
			"width": 100
		},
		{
			"fieldname": "inst_date",
			"label": _("Installation Date"),
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
			"fieldname": "item_code",
			"label": _("Item code"),
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
	
	installation_note = frappe.qb.DocType("Installation Note")
	delivery_note_item = frappe.qb.DocType("Delivery Note Item")
	query = (
		frappe.qb.from_(installation_note)
		.left_join(delivery_note_item)
		.on(delivery_note_item.parent == installation_note.delivery_note)
		.select(
			installation_note.name.as_("reference"),
			installation_note.inst_date,
			installation_note.customer,
			installation_note.item_code,
			installation_note.remarks,
			installation_note.status,
			installation_note.delivery_note,
			delivery_note_item.warehouse,
		)
		.where(installation_note.docstatus != 2)
		.where(installation_note.inst_date[filters.from_date:filters.to_date])
	)

	if filters.branch:
		query = query.where(delivery_note_item.warehouse == filters.branch)

	data = query.run(as_dict=1)
						 
	return columns, data
