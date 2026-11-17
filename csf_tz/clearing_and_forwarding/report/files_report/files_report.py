# Copyright (c) 2013, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
from frappe.query_builder import Case, Criterion
from frappe.query_builder.functions import Sum
import ast
from datetime import datetime

def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "file_no",
			"label": _("File No"),
			"fieldtype": "Link",
			"options": "Files",
			"width": 100
		},
		{
			"fieldname": "file_type",
			"label": _("File Type"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "documents_received_date",
			"label": _("Document Received"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "location",
			"label": _("Opening Location"),
			"fieldtype": "Link",
			"options": "Locations",
			"width": 200
		},
		{
			"fieldname": "expenses_usd",
			"label": _("Expenses(USD)"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "expenses_tzs",
			"label": _("Expenses(TZS)"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "invoiced_amount_usd",
			"label": _("Invoiced Amount(USD)"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "invoiced_amount_tzs",
			"label": _("Invoiced Amount(TZS)"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "paid_amount_usd",
			"label": _("Paid Amount(USD)"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "paid_amount_tzs",
			"label": _("Paid Amount(TZS)"),
			"fieldtype": "Float",
			"width": 150
		}
	]
	
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))
	
	files = frappe.qb.DocType("Files")
	data = (
		frappe.qb.from_(files)
		.select(
			files.name.as_("file_no"),
			Case()
			.when(files.import_transit == 1, 'Importation - Transit')
			.when(files.import_local == 1, 'Importation - Local')
			.when(files.export_transit == 1, 'Export - Transit')
			.when(files.export_local == 1, 'Export Local')
			.when(files.transport_transit == 1, 'Transport - Transit')
			.when(files.transport_local == 1, 'Transport - Local')
			.when(files.border_clearance == 1, 'Border Clearance')
			.as_("file_type"),
			files.documents_received_date,
			files.customer,
			files.location,
			get_expenses_total(files, 'USD').as_("expenses_usd"),
			get_expenses_total(files, 'TZS').as_("expenses_tzs"),
			get_invoiced_total(files, 'USD').as_("invoiced_amount_usd"),
			get_invoiced_total(files, 'TZS').as_("invoiced_amount_tzs"),
			get_paid_amount(files, 'USD').as_("paid_amount_usd"),
			get_paid_amount(files, 'TZS').as_("paid_amount_tzs"),
		)
		.where(files.documents_received_date[filters.from_date:filters.to_date])
		.run(as_dict=True)
	)
	return columns, data


def get_expenses_total(files, currency):
	expenses = frappe.qb.DocType("Expenses")
	belongs_to_file = Criterion.any([
		get_linked_parent_condition(expenses, "Import", "reference_file_number", files),
		get_linked_parent_condition(expenses, "Export", "file_number", files),
		get_linked_parent_condition(expenses, "Vehicle Trip", "main_file_number", files),
		get_linked_parent_condition(expenses, "Vehicle Trip", "return_file_number", files),
		get_linked_parent_condition(expenses, "Border Clearance", "file_number", files),
		(expenses.parenttype == 'Files') & (expenses.parent == files.name),
	])
	return (
		frappe.qb.from_(expenses)
		.select(Sum(expenses.expense_amount))
		.where(expenses.expense_currency == currency)
		.where(belongs_to_file)
	)


def get_linked_parent_condition(expenses, parenttype, file_number_field, files):
	parent = frappe.qb.DocType(parenttype)
	linked_parents = frappe.qb.from_(parent).select(parent.name).where(parent[file_number_field] == files.name)
	return (expenses.parenttype == parenttype) & expenses.parent.isin(linked_parents)


def get_file_invoices(files):
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	return (
		frappe.qb.from_(sales_invoice)
		.where(sales_invoice.reference_doctype == 'Files')
		.where(sales_invoice.reference_docname == files.name)
	)


def get_invoiced_total(files, currency):
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	return get_file_invoices(files).select(Sum(sales_invoice.grand_total)).where(sales_invoice.currency == currency)


def get_paid_amount(files, currency):
	gl_entry = frappe.qb.DocType("GL Entry")
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	return (
		frappe.qb.from_(gl_entry)
		.select(gl_entry.credit_in_account_currency)
		.where(gl_entry.credit_in_account_currency > 0)
		.where(gl_entry.account_currency == currency)
		.where(gl_entry.against_voucher_type == 'Sales Invoice')
		.where(gl_entry.against_voucher.isin(get_file_invoices(files).select(sales_invoice.name)))
	)
