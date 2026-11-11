# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import Criterion, Order
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import flt, getdate, cstr


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
            "width": 150
        },
        {
            "fieldname": "purchase_invoice",
            "label": _("Purchase Invoice"),
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "width": 150
        },
        {
            "fieldname": "supplier",
            "label": _("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 150
        },
        {
            "fieldname": "transaction_date",
            "label": _("Transaction Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "currency",
            "label": _("Currency"),
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80
        },
        {
            "fieldname": "original_exchange_rate",
            "label": _("Original Rate"),
            "fieldtype": "Float",
            "precision": 4,
            "width": 100
        },
        {
            "fieldname": "invoice_amount_foreign",
            "label": _("Invoice Amount (Foreign)"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },
        {
            "fieldname": "invoice_amount_base",
            "label": _("Invoice Amount (Base)"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "total_payments",
            "label": _("Total Payments"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120
        },
        {
            "fieldname": "payment_differences",
            "label": _("Payment Differences"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "lcv_differences",
            "label": _("LCV Differences"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "total_gain_loss",
            "label": _("Total Gain/Loss"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        }
    ]


def get_data(filters):
    foreign_import_transaction = frappe.qb.DocType("Foreign Import Transaction")
    payment_details = frappe.qb.DocType("Foreign Import Payment Details")
    lcv_details = frappe.qb.DocType("Foreign Import LCV Details")

    payment_summary = (
        frappe.qb.from_(payment_details)
        .select(
            payment_details.parent,
            Sum(payment_details.payment_amount_foreign).as_("total_payments"),
            Sum(payment_details.exchange_difference).as_("payment_differences"),
        )
        .groupby(payment_details.parent)
    ).as_("payment_summary")
    lcv_summary = (
        frappe.qb.from_(lcv_details)
        .select(lcv_details.parent, Sum(lcv_details.exchange_difference).as_("lcv_differences"))
        .groupby(lcv_details.parent)
    ).as_("lcv_summary")

    query = (
        frappe.qb.from_(foreign_import_transaction)
        .left_join(payment_summary)
        .on(payment_summary.parent == foreign_import_transaction.name)
        .left_join(lcv_summary)
        .on(lcv_summary.parent == foreign_import_transaction.name)
        .select(
            foreign_import_transaction.name.as_("foreign_import_transaction"),
            foreign_import_transaction.purchase_invoice,
            foreign_import_transaction.supplier,
            foreign_import_transaction.transaction_date,
            foreign_import_transaction.currency,
            foreign_import_transaction.original_exchange_rate,
            foreign_import_transaction.invoice_amount_foreign,
            foreign_import_transaction.invoice_amount_base,
            foreign_import_transaction.total_gain_loss,
            foreign_import_transaction.status,
            Coalesce(payment_summary.total_payments, 0).as_("total_payments"),
            Coalesce(payment_summary.payment_differences, 0).as_("payment_differences"),
            Coalesce(lcv_summary.lcv_differences, 0).as_("lcv_differences"),
        )
        .where(foreign_import_transaction.docstatus == 1)
        .orderby(foreign_import_transaction.transaction_date, order=Order.desc)
        .orderby(foreign_import_transaction.name)
    )
    return query.where(Criterion.all(get_conditions(filters, foreign_import_transaction))).run(as_dict=True)


def get_conditions(filters, foreign_import_transaction):
    conditions = []
    
    if filters.get("company"):
        conditions.append(foreign_import_transaction.company == filters.get("company"))
    
    if filters.get("from_date"):
        conditions.append(foreign_import_transaction.transaction_date >= filters.get("from_date"))
    
    if filters.get("to_date"):
        conditions.append(foreign_import_transaction.transaction_date <= filters.get("to_date"))
    
    if filters.get("purchase_invoice"):
        conditions.append(foreign_import_transaction.purchase_invoice == filters.get("purchase_invoice"))
    
    if filters.get("supplier"):
        conditions.append(foreign_import_transaction.supplier == filters.get("supplier"))
    
    if filters.get("currency"):
        conditions.append(foreign_import_transaction.currency == filters.get("currency"))
    
    if filters.get("status"):
        conditions.append(foreign_import_transaction.status == filters.get("status"))
    
    return conditions
