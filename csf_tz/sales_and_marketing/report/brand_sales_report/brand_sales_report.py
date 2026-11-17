# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from csf_tz.sales_and_marketing.customer_address import get_customer_address


def execute(filters=None):
	columns, data = [], []
	columns = [
		{"fieldname": "posting_date", "label": _("Sale Date"), "fieldtype": "Date", "width": 150},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
		{
			"fieldname": "customer_address",
			"label": _("Customer Address"),
			"fieldtype": "Small Text",
			"width": 200,
		},
		{"fieldname": "contact", "label": _("Customer Contacts"), "fieldtype": "Small Text", "width": 150},
		{"fieldname": "itm", "label": _("Item Sold"), "fieldtype": "Link", "options": "Item", "width": 200},
		{
			"fieldname": "brand",
			"label": _("Brand"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150,
		},
		{"fieldname": "quantity", "label": _("Quantity"), "fieldtype": "data", "width": 150},
	]

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	invoice_item = frappe.qb.DocType("Sales Invoice Item")
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(invoice_item)
		.left_join(sales_invoice)
		.on(sales_invoice.name == invoice_item.parent)
		.left_join(item)
		.on(item.item_code == invoice_item.item_code)
		.select(
			sales_invoice.customer,
			sales_invoice.name,
			sales_invoice.posting_date,
			sales_invoice.grand_total,
			invoice_item.warehouse,
			invoice_item.item_code.as_("itm"),
			invoice_item.qty.as_("quantity"),
			item.brand.as_("brand"),
			invoice_item.parent.as_("si_name"),
			sales_invoice.customer.as_("cust"),
		)
		.where(sales_invoice.docstatus == 1)
		.where(item.item_group != "Spare Parts")
		.where(sales_invoice.customer != "Guest")
		.where(sales_invoice.posting_date[filters.from_date : filters.to_date])
	)

	if filters.customer:
		query = query.where(sales_invoice.customer == filters.customer)

	if filters.brand:
		query = query.where(item.brand == filters.brand)

	data = query.run(as_dict=True)

	for customer in data:
		address = get_customer_address(customer.customer)
		if address:
			customer.update(address)

	return columns, data
