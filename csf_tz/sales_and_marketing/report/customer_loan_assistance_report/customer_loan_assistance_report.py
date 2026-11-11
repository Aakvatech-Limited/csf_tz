# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Date


def execute(filters=None):
	if not frappe.db.exists("DocType", "Customer Loan Assistance"):
		frappe.throw(_("DocType Customer Loan Assistance is not installed on this site"))

	columns, data = [], []

	columns = [
		{
			"fieldname": "reference",
			"label": _("Reference"),
			"fieldtype": "Link",
			"options": "Customer Loan Assistance",
			"width": 150,
		},
		{
			"fieldname": "customer_type",
			"label": _("Lead / Customer"),
			"fieldtype": "Link",
			"options": "Doctype",
			"width": 150,
			"hidden": 1,
		},
		{
			"fieldname": "customer_reference",
			"label": _("Customer Reference"),
			"fieldtype": "Dynamic Link",
			"options": "customer_type",
			"width": 150,
		},
		{"fieldname": "customer_name", "label": _("Customer Name"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "loan_supplier",
			"label": _("Loan Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150,
		},
		{"fieldname": "start_date", "label": _("Start Date"), "fieldtype": "Date", "width": 150},
		{"fieldname": "end_date", "label": _("End Date"), "fieldtype": "Date", "width": 150},
		{
			"fieldname": "loan_status",
			"label": _("Loan Status"),
			"fieldtype": "Dynamic Link",
			"options": "customer_type",
			"width": 150,
		},
	]

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	loan_assistance = frappe.qb.DocType("Customer Loan Assistance")
	has_customer = loan_assistance.customer.isnotnull()
	query = (
		frappe.qb.from_(loan_assistance)
		.select(
			loan_assistance.name.as_("reference"),
			Case().when(has_customer, "Customer").else_("Lead").as_("customer_type"),
			Case()
			.when(has_customer, loan_assistance.customer)
			.else_(loan_assistance.lead)
			.as_("customer_reference"),
			Case()
			.when(has_customer, loan_assistance.customer)
			.else_(loan_assistance.lead_name)
			.as_("customer_name"),
			loan_assistance.loan_supplier,
			Date(loan_assistance.creation).as_("start_date"),
			loan_assistance.completion_date.as_("end_date"),
			loan_assistance.loan_status,
		)
		.where(loan_assistance.creation[filters.from_date : filters.to_date])
	)
	if filters.loan_supplier:
		query = query.where(loan_assistance.loan_supplier == filters.loan_supplier)

	data = query.run(as_dict=True)
	return columns, data
