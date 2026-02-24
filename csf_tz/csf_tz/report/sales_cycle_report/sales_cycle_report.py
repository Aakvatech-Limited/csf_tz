# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Row Labels"),
            "fieldname": "row_labels",
            "fieldtype": "Link",
            "options": "Sales Order",
            "width": 200,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150,
        },
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150,
        },
        {
            "label": _("Sum of Qty"),
            "fieldname": "sum_qty",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": _("Sum of Delivered Qty"),
            "fieldname": "sum_delivered_qty",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": _("Sum of Pending Delivery Qty"),
            "fieldname": "sum_pending_delivery_qty",
            "fieldtype": "Float",
            "width": 150,
        },
        {
            "label": _("Sum of Billed Qty"),
            "fieldname": "sum_billed_qty",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": _("Sum of Qty to Invoice"),
            "fieldname": "sum_qty_to_invoice",
            "fieldtype": "Float",
            "width": 150,
        },
        {
            "label": _("Sum of Amount"),
            "fieldname": "sum_amount",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "label": _("Sum of Billed Amount"),
            "fieldname": "sum_billed_amount",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "label": _("Sum of Pending Amount"),
            "fieldname": "sum_pending_amount",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "label": _("Sum of Delivered Amount"),
            "fieldname": "sum_delivered_amount",
            "fieldtype": "Currency",
            "width": 150,
        },
    ]


def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    item_type = filters.get("item_type")  # 'Stock' or 'Non-Stock/Service'
    warehouse = filters.get("warehouse")

    # Ensure from_date starts from the first day of the month
    if from_date:
        from_date_obj = frappe.utils.getdate(from_date)
        from_date = frappe.utils.get_first_day(from_date_obj).strftime('%Y-%m-%d')

    # Use Query Builder for complex joins and sums
    SO = DocType("Sales Order")
    SOI = DocType("Sales Order Item")
    Item = DocType("Item")

    qb = frappe.qb
    query = (
        qb.from_(SO)
        .inner_join(SOI)
        .on(SOI.parent == SO.name)
        .inner_join(Item)
        .on(Item.name == SOI.item_code)
        .where(SO.docstatus == 1)
        .where(SO.transaction_date.between(from_date, to_date))
        .select(
            SOI.warehouse.as_("warehouse"),
            SO.status.as_("status"),
            SO.name.as_("row_labels"),
            SO.customer.as_("customer"),
            SOI.item_code.as_("item_code"),
            Sum(SOI.qty).as_("sum_qty"),
            Sum(SOI.delivered_qty).as_("sum_delivered_qty"),
            Sum(SOI.qty - SOI.delivered_qty).as_("sum_pending_delivery_qty"),
            Sum(SOI.billed_amt / SOI.rate).as_("sum_billed_qty"),
            Sum(SOI.delivered_qty - (SOI.billed_amt / SOI.rate)).as_("sum_qty_to_invoice"),
            Sum(SOI.amount).as_("sum_amount"),
            Sum(SOI.billed_amt).as_("sum_billed_amount"),
            Sum(SOI.amount - SOI.billed_amt).as_("sum_pending_amount"),
            Sum(SOI.delivered_qty * SOI.rate).as_("sum_delivered_amount"),
        )
        .groupby(SOI.warehouse, SO.status, SO.name, SO.customer, SOI.item_code)
        .orderby(SOI.warehouse, SO.status, SO.name, SOI.item_code)
    )

    # Apply optional filters
    if item_type == "Stock":
        query = query.where(Item.is_stock_item == 1)
    elif item_type == "Non-Stock/Service":
        query = query.where(Item.is_stock_item == 0)
    if warehouse:
        query = query.where(SOI.warehouse == warehouse)

    data = query.run(as_dict=True)

    # Post-process with ORM if needed (e.g., fetch additional details)
    if not data:  # Fallback or additional simple fetches
        data = frappe.get_all(
            "Sales Order",
            filters={"transaction_date": ["between", [from_date, to_date]]},
            fields=["name", "status"],
        )

    return data
