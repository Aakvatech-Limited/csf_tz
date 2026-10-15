# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{
			"fieldname": "foreign_import_transaction",
			"label": _("Import Transaction"),
			"fieldtype": "Link",
			"options": "Foreign Import Transaction",
			"width": 150,
		},
		{
			"fieldname": "purchase_invoice",
			"label": _("Purchase Invoice"),
			"fieldtype": "Link",
			"options": "Purchase Invoice",
			"width": 150,
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150,
		},
		{"fieldname": "transaction_date", "label": _("Transaction Date"), "fieldtype": "Date", "width": 100},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80,
		},
		{
			"fieldname": "original_exchange_rate",
			"label": _("Original Rate"),
			"fieldtype": "Float",
			"precision": 4,
			"width": 100,
		},
		{
			"fieldname": "invoice_amount_foreign",
			"label": _("Invoice Amount (Foreign)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "invoice_amount_base",
			"label": _("Invoice Amount (Base)"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "total_payments",
			"label": _("Total Payments"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "payment_differences",
			"label": _("Payment Differences"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "lcv_differences",
			"label": _("LCV Differences"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "total_gain_loss",
			"label": _("Total Gain/Loss"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	from frappe.query_builder.functions import Coalesce, Sum

	fit = frappe.qb.DocType("Foreign Import Transaction")
	payment = frappe.qb.DocType("Foreign Import Payment Details")
	lcv = frappe.qb.DocType("Foreign Import LCV Details")
	payment_summary = (
		frappe.qb.from_(payment)
		.select(
			payment.parent,
			Sum(payment.payment_amount_foreign).as_("total_payments"),
			Sum(payment.exchange_difference).as_("payment_differences"),
		)
		.groupby(payment.parent)
	).as_("payment_summary")
	lcv_summary = (
		frappe.qb.from_(lcv)
		.select(lcv.parent, Sum(lcv.exchange_difference).as_("lcv_differences"))
		.groupby(lcv.parent)
	).as_("lcv_summary")

	query = (
		frappe.qb.from_(fit)
		.left_join(payment_summary)
		.on(payment_summary.parent == fit.name)
		.left_join(lcv_summary)
		.on(lcv_summary.parent == fit.name)
		.select(
			fit.name.as_("foreign_import_transaction"),
			fit.purchase_invoice,
			fit.supplier,
			fit.transaction_date,
			fit.currency,
			fit.original_exchange_rate,
			fit.invoice_amount_foreign,
			fit.invoice_amount_base,
			fit.total_gain_loss,
			fit.status,
			Coalesce(payment_summary.total_payments, 0).as_("total_payments"),
			Coalesce(payment_summary.payment_differences, 0).as_("payment_differences"),
			Coalesce(lcv_summary.lcv_differences, 0).as_("lcv_differences"),
		)
		.where(fit.docstatus == 1)
		.orderby(fit.transaction_date, order=frappe.qb.terms.Order.desc)
		.orderby(fit.name)
	)
	for field in ("company", "purchase_invoice", "supplier", "currency", "status"):
		if filters.get(field):
			query = query.where(getattr(fit, field) == filters[field])
	if filters.get("from_date"):
		query = query.where(fit.transaction_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(fit.transaction_date <= filters["to_date"])
	return query.run(as_dict=True)
