# Copyright (c) 2026, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import functions as qb_functions
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    apply_defaults(filters)
    validate_filters(filters)

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def apply_defaults(filters):
    if not filters.get("price_list"):
        default_price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
        if default_price_list:
            filters.price_list = default_price_list
        else:
            filters.price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")


def validate_filters(filters):
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are required"))

    if getdate(filters.to_date) < getdate(filters.from_date):
        frappe.throw(_("To Date must be on or after From Date"))

    if not filters.get("price_list"):
        frappe.throw(_("Price List is required"))


def get_columns():
    return [
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 140,
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Item Group"),
            "fieldname": "item_group",
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 160,
        },
        {
            "label": _("Last Purchase Price"),
            "fieldname": "last_purchase_price",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": _("Valuation Rate (FIFO)"),
            "fieldname": "valuation_rate",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": _("Current Selling Price"),
            "fieldname": "current_selling_price",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": _("Quantity Sold"),
            "fieldname": "qty_sold",
            "fieldtype": "Float",
            "width": 120,
        },
        {
            "label": _("Available Quantity"),
            "fieldname": "available_qty",
            "fieldtype": "Float",
            "width": 140,
        },
    ]


def get_data(filters):
    Item = frappe.qb.DocType("Item")
    items = (
        frappe.qb.from_(Item)
        .select(
            Item.name.as_("item_code"),
            Item.item_name,
            Item.item_group,
            Item.last_purchase_rate,
        )
        .where(Item.disabled == 0)
        .run(as_dict=True)
    )

    sold_map = get_quantity_sold(filters)
    bin_map = get_bin_snapshot(filters)
    price_map = get_current_selling_prices(filters)

    data = []
    for item in items:
        item_code = item.item_code
        bin_row = bin_map.get(item_code, {})

        data.append(
            {
                "item_code": item_code,
                "item_name": item.item_name,
                "item_group": item.item_group,
                "last_purchase_price": flt(item.last_purchase_rate),
                "valuation_rate": flt(bin_row.get("valuation_rate")),
                "current_selling_price": flt(price_map.get(item_code)),
                "qty_sold": flt(sold_map.get(item_code)),
                "available_qty": flt(bin_row.get("available_qty")),
            }
        )

    return data


def get_quantity_sold(filters):
    SalesInvoice = frappe.qb.DocType("Sales Invoice")
    SalesInvoiceItem = frappe.qb.DocType("Sales Invoice Item")

    rows = (
        frappe.qb.from_(SalesInvoiceItem)
        .join(SalesInvoice)
        .on(SalesInvoice.name == SalesInvoiceItem.parent)
        .select(
            SalesInvoiceItem.item_code,
            qb_functions.Sum(SalesInvoiceItem.stock_qty).as_("qty_sold"),
        )
        .where(SalesInvoice.docstatus == 1)
        .where(SalesInvoice.posting_date.between(filters.from_date, filters.to_date))
        .groupby(SalesInvoiceItem.item_code)
        .run(as_dict=True)
    )

    return {row.item_code: row.qty_sold for row in rows}


def get_bin_snapshot(filters):
    Bin = frappe.qb.DocType("Bin")

    query = (
        frappe.qb.from_(Bin)
        .select(
            Bin.item_code,
            qb_functions.Sum(Bin.actual_qty).as_("available_qty"),
            qb_functions.Sum(Bin.stock_value).as_("stock_value"),
        )
        .groupby(Bin.item_code)
    )

    if filters.get("warehouse"):
        query = query.where(Bin.warehouse == filters.warehouse)

    rows = query.run(as_dict=True)

    for row in rows:
        total_qty = flt(row.get("available_qty"))
        row["valuation_rate"] = flt(row.get("stock_value")) / total_qty if total_qty else 0

    return {row.item_code: row for row in rows}


def get_current_selling_prices(filters):
    today = nowdate()
    ItemPrice = frappe.qb.DocType("Item Price")

    rows = (
        frappe.qb.from_(ItemPrice)
        .select(
            ItemPrice.item_code,
            ItemPrice.price_list_rate,
            ItemPrice.valid_from,
            ItemPrice.modified,
        )
        .where(ItemPrice.price_list == filters.price_list)
        .where(ItemPrice.selling == 1)
        .where(ItemPrice.valid_from.isnull() | (ItemPrice.valid_from <= today))
        .where(ItemPrice.valid_upto.isnull() | (ItemPrice.valid_upto >= today))
        .orderby(ItemPrice.item_code)
        .orderby(qb_functions.IfNull(ItemPrice.valid_from, "1900-01-01"), order=frappe.qb.desc)
        .orderby(ItemPrice.modified, order=frappe.qb.desc)
        .run(as_dict=True)
    )

    price_map = {}
    for row in rows:
        if row.item_code not in price_map:
            price_map[row.item_code] = row.price_list_rate

    return price_map
