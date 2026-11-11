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
    purchase_order = frappe.qb.DocType("Purchase Order")
    purchase_order_item = frappe.qb.DocType("Purchase Order Item")
    query = (
        frappe.qb.from_(purchase_order_item)
        .join(purchase_order)
        .on(purchase_order_item.parent == purchase_order.name)
        .select(
            purchase_order.name.as_("purchase_order"),
            purchase_order.supplier,
            purchase_order_item.item_code,
            purchase_order_item.warehouse,
            purchase_order.status,
            purchase_order_item.qty,
            purchase_order_item.received_qty,
            (purchase_order_item.qty - purchase_order_item.received_qty).as_("pending_qty"),
            purchase_order_item.amount,
            purchase_order_item.billed_amt.as_("billed_amount"),
            (purchase_order_item.amount - purchase_order_item.billed_amt).as_("pending_amount"),
            (purchase_order_item.received_qty * purchase_order_item.rate).as_("received_qty_amount"),
        )
        .where(purchase_order.docstatus == 1)
        .orderby(purchase_order.status)
        .orderby(purchase_order.name)
    )
    if filters.get("from_date"):
        query = query.where(purchase_order.transaction_date >= filters.get("from_date"))
    if filters.get("to_date"):
        query = query.where(purchase_order.transaction_date <= filters.get("to_date"))

    data = query.run(as_dict=True)

    return data
