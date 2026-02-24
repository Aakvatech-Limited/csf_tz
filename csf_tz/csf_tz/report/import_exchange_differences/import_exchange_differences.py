# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
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
    conditions = get_conditions(filters)
    
    query = """
        SELECT 
            fit.name as foreign_import_transaction,
            fit.purchase_invoice,
            fit.supplier,
            fit.transaction_date,
            fit.currency,
            fit.original_exchange_rate,
            fit.invoice_amount_foreign,
            fit.invoice_amount_base,
            fit.total_gain_loss,
            fit.status,
            COALESCE(payment_summary.total_payments, 0) as total_payments,
            COALESCE(payment_summary.payment_differences, 0) as payment_differences,
            COALESCE(lcv_summary.lcv_differences, 0) as lcv_differences
        FROM `tabForeign Import Transaction` fit
        LEFT JOIN (
            SELECT 
                parent,
                SUM(payment_amount_foreign) as total_payments,
                SUM(exchange_difference) as payment_differences
            FROM `tabForeign Import Payment Details`
            GROUP BY parent
        ) payment_summary ON payment_summary.parent = fit.name
        LEFT JOIN (
            SELECT 
                parent,
                SUM(exchange_difference) as lcv_differences
            FROM `tabForeign Import LCV Details`
            GROUP BY parent
        ) lcv_summary ON lcv_summary.parent = fit.name
        WHERE fit.docstatus = 1 {conditions}
        ORDER BY fit.transaction_date DESC, fit.name
    """.format(conditions=conditions)
    
    data = frappe.db.sql(query, filters, as_dict=1)
    
    return data


def get_conditions(filters):
    conditions = []
    
    if filters.get("company"):
        conditions.append("AND fit.company = %(company)s")
    
    if filters.get("from_date"):
        conditions.append("AND fit.transaction_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("AND fit.transaction_date <= %(to_date)s")
    
    if filters.get("purchase_invoice"):
        conditions.append("AND fit.purchase_invoice = %(purchase_invoice)s")
    
    if filters.get("supplier"):
        conditions.append("AND fit.supplier = %(supplier)s")
    
    if filters.get("currency"):
        conditions.append("AND fit.currency = %(currency)s")
    
    if filters.get("status"):
        conditions.append("AND fit.status = %(status)s")
    
    return " ".join(conditions)
