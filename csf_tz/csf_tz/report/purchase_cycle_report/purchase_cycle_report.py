# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {"label": "Purchase Order", "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 150},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 180},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},

        {"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "width": 100},
        {"label": "Received Qty", "fieldname": "received_qty", "fieldtype": "Float", "width": 110},
        {"label": "Pending Qty", "fieldname": "pending_qty", "fieldtype": "Float", "width": 110},
        # Removed Billed Qty and Qty to Bill columns as billed_qty does not exist

        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
        {"label": "Billed Amount", "fieldname": "billed_amount", "fieldtype": "Currency", "width": 130},
        {"label": "Pending Amount", "fieldname": "pending_amount", "fieldtype": "Currency", "width": 130},
        {"label": "Received Qty Amount", "fieldname": "received_qty_amount", "fieldtype": "Currency", "width": 150},
    ]


def get_data(filters):
    conditions = ""
    if filters.get("from_date"):
        conditions += " and po.transaction_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " and po.transaction_date <= %(to_date)s"

    data = frappe.db.sql(f"""
        SELECT
            po.name as purchase_order,
            po.supplier,
            poi.item_code,
            poi.warehouse,
            po.status,

            poi.qty as qty,
            poi.received_qty as received_qty,
            (poi.qty - poi.received_qty) as pending_qty,
                -- Removed billed_qty and qty_to_bill as billed_qty does not exist

            poi.amount as amount,
            poi.billed_amt as billed_amount,
            (poi.amount - poi.billed_amt) as pending_amount,
            (poi.received_qty * poi.rate) as received_qty_amount

        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON poi.parent = po.name
        WHERE po.docstatus = 1 {conditions}
        ORDER BY po.status, po.name
    """, filters, as_dict=True)

    return data
