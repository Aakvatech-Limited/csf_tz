# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Sum


def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "name",
			"label" : _("Material Request"),
			"fieldtype": "Link",
			"options": "Material Request"
		},
		{
			"fieldname": "transaction_date",
			"label": _("Date "),
			"fieldtype": "Date",
		},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
		},
		{
			"fieldname": "qty",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "ordered_qty",
			"label": _("Ordered Qty"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "qty_to_order",
			"label": _("Qty To Order"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "item_name",
			"label": _("Item Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 150
		},
		
	]
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	material_request = frappe.qb.DocType("Material Request")
	material_request_item = frappe.qb.DocType("Material Request Item")
	query = (
		frappe.qb.from_(material_request)
		.join(material_request_item)
		.on(material_request_item.parent == material_request.name)
		.select(
			material_request.name,
			material_request.transaction_date,
			material_request.company,
			material_request_item.item_code,
			Sum(IfNull(material_request_item.qty, 0)).as_("qty"),
			Sum(IfNull(material_request_item.ordered_qty, 0)).as_("ordered_qty"),
			(Sum(material_request_item.qty) - Sum(IfNull(material_request_item.ordered_qty, 0))).as_("qty_to_order"),
			material_request_item.item_name,
			material_request_item.description,
			material_request.company,
		)
		.where(material_request.material_request_type == "Purchase")
		.where(material_request.docstatus == 1)
		.where(material_request.status != "Stopped")
		.where(material_request.transaction_date[filters.from_date:filters.to_date])
		.groupby(material_request.name, material_request_item.item_code)
		.having(Sum(IfNull(material_request_item.ordered_qty, 0)) < Sum(IfNull(material_request_item.qty, 0)))
	)

	if filters.material_request:
		query = query.having(material_request.name == filters.material_request)
	if filters.item_code:
		query = query.having(material_request_item.item_code == filters.item_code)

	data = query.run(as_dict=1)

	return columns, data
