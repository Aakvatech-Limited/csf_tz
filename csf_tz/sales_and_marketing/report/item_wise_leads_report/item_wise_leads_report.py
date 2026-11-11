# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder.functions import Count, Sum


def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "item_code",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 200
		},
		{
			"fieldname": "total_qty",
			"label": _("Quantity"),
			"fieldtype": "Float",
		},
		{
			"fieldname": "quotations",
			"label" : _("Quotations"),
			"fieldtype": "int",
			"width": 150
		},
		{
			"fieldname": "customers",
			"label": _("Customers"),
			"fieldtype": "Int",
			"width": 150
		},
		{
			"fieldname": "leads",
			"label": _("Leads"),
			"fieldtype": "Int",
			"width": 150
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 200
		},
	]
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	quotation_item = frappe.qb.DocType("Quotation Item")
	quotation = frappe.qb.DocType("Quotation")
	customer_quotation = frappe.qb.DocType("Quotation").as_("customer_quot")
	data = (
		frappe.qb.from_(quotation_item)
		.left_join(quotation).on(quotation_item.parent == quotation.name)
		.left_join(customer_quotation).on(
			(quotation_item.parent == customer_quotation.name) & (customer_quotation.quotation_to == 'Customer')
		)
		.select(
			quotation_item.item_code,
			quotation_item.item_name,
			Sum(quotation_item.qty).as_("total_qty"),
			Count(quotation.name).as_("quotations"),
			Count(customer_quotation.customer).distinct().as_("customers"),
			Count(quotation.lead).distinct().as_("leads"),
			quotation_item.warehouse,
		)
		.where(quotation.docstatus == 1)
		.where(quotation.transaction_date[filters.from_date:filters.to_date])
		.groupby(quotation_item.item_code, quotation_item.warehouse)
		.run(as_dict=True)
	)
	return columns, data
