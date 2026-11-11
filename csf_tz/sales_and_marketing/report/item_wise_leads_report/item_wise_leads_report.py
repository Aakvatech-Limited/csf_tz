# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Sum


def execute(filters=None):
	columns, data = [], []
	columns = [
		{"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 200},
		{
			"fieldname": "total_qty",
			"label": _("Quantity"),
			"fieldtype": "Float",
		},
		{"fieldname": "quotations", "label": _("Quotations"), "fieldtype": "int", "width": 150},
		{"fieldname": "customers", "label": _("Customers"), "fieldtype": "Int", "width": 150},
		{"fieldname": "leads", "label": _("Leads"), "fieldtype": "Int", "width": 150},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 200,
		},
	]
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	quotation_item = frappe.qb.DocType("Quotation Item")
	quotation = frappe.qb.DocType("Quotation")
	data = (
		frappe.qb.from_(quotation_item)
		.left_join(quotation)
		.on(quotation_item.parent == quotation.name)
		.select(
			quotation_item.item_code,
			quotation_item.item_name,
			Sum(quotation_item.qty).as_("total_qty"),
			Count(quotation.name).as_("quotations"),
			Count(party_of_type(quotation, "Customer")).distinct().as_("customers"),
			Count(party_of_type(quotation, "Lead")).distinct().as_("leads"),
			quotation_item.warehouse,
		)
		.where(quotation.docstatus == 1)
		.where(quotation.transaction_date[filters.from_date : filters.to_date])
		.groupby(quotation_item.item_code, quotation_item.warehouse)
		.run(as_dict=True)
	)
	return columns, data


def party_of_type(quotation, quotation_to):
	return Case().when(quotation.quotation_to == quotation_to, quotation.party_name)
