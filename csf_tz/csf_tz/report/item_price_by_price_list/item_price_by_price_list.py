# Copyright (c) 2026, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today


def execute(filters=None):
    filters = frappe._dict(filters or {})

    price_lists = get_price_lists(filters)
    columns = get_columns(price_lists)
    items = get_items(filters)

    if not items:
        return columns, []

    item_codes = [row.item_code for row in items]
    item_uom_map = {row.item_code: row.stock_uom for row in items}

    bin_rows = get_bin_rows(item_codes, filters)
    qty_map, value_map, warehouse_map = build_bin_maps(bin_rows)

    price_rows = get_price_rows(item_codes, [row.name for row in price_lists])
    price_map = build_price_map(price_rows, item_uom_map)

    data = build_data(
        items,
        price_lists,
        price_map,
        qty_map,
        value_map,
        warehouse_map,
        filters,
    )

    return columns, data


def get_price_lists(filters):
    PriceList = frappe.qb.DocType("Price List")

    query = (
        frappe.qb.from_(PriceList)
        .select(PriceList.name, PriceList.currency)
        .where(PriceList.selling == 1)
    )

    if filters.get("price_list"):
        query = query.where(PriceList.name == filters.price_list)

    return query.orderby(PriceList.name).run(as_dict=True)


def get_columns(price_lists):
    columns = [
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 180,
        },
        {
            "label": _("Item Description"),
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "label": _("Default Item Tax Template"),
            "fieldname": "default_tax_template",
            "fieldtype": "Link",
            "options": "Item Tax Template",
            "width": 180,
        },
    ]

    for price_list in price_lists:
        field_base = get_price_field_base(price_list.name)
        columns.append(
            {
                "label": _(price_list.name + " Excl"),
                "fieldname": field_base + "_excl",
                "fieldtype": "Currency",
                "options": price_list.currency,
                "width": 130,
            }
        )

    for price_list in price_lists:
        field_base = get_price_field_base(price_list.name)
        columns.append(
            {
                "label": _(price_list.name + " Rate"),
                "fieldname": field_base,
                "fieldtype": "Currency",
                "options": price_list.currency,
                "width": 130,
            }
        )

    columns.extend(
        [
            {
                "label": _("Total Qty"),
                "fieldname": "total_qty",
                "fieldtype": "Float",
                "width": 110,
            },
            {
                "label": _("Last Purchase Rate"),
                "fieldname": "last_purchase_rate",
                "fieldtype": "Currency",
                "width": 140,
            },
            {
                "label": _("Valuation Rate"),
                "fieldname": "valuation_rate",
                "fieldtype": "Currency",
                "width": 130,
            },
            {
                "label": _("Warehouse Qty"),
                "fieldname": "warehouse_qty",
                "fieldtype": "Data",
                "width": 300,
            },
        ]
    )

    return columns


def get_price_field_base(price_list):
    return "rate_" + price_list.replace(" ", "_").lower()


def get_items(filters):
    Item = frappe.qb.DocType("Item")

    query = (
        frappe.qb.from_(Item)
        .select(
            Item.item_code,
            Item.description,
            Item.last_purchase_rate,
            Item.stock_uom,
            Item.item_group,
        )
        .where(Item.disabled == 0)
        .where(Item.is_sales_item == 1)
    )

    # default_tax_template is a csf_tz custom field; skip it on sites where it was never created
    if frappe.db.has_column("Item", "default_tax_template"):
        query = query.select(Item.default_tax_template)

    barcode = filters.get("barcode")
    search_text = filters.get("item_description")

    if barcode:
        ItemBarcode = frappe.qb.DocType("Item Barcode")
        barcode_rows = (
            frappe.qb.from_(ItemBarcode)
            .select(ItemBarcode.parent)
            .where(ItemBarcode.barcode == barcode)
            .run(as_dict=True)
        )

        if not barcode_rows:
            return []

        query = query.where(Item.item_code == barcode_rows[0].parent)
    elif search_text:
        query = query.where(
            (Item.description.like("%" + search_text + "%"))
            | (Item.item_code == search_text)
        )

    if filters.get("item_group"):
        query = query.where(Item.item_group == filters.item_group)

    return query.orderby(Item.item_code).run(as_dict=True)


def get_bin_rows(item_codes, filters):
    if not item_codes:
        return []

    Bin = frappe.qb.DocType("Bin")

    query = (
        frappe.qb.from_(Bin)
        .select(Bin.item_code, Bin.warehouse, Bin.actual_qty, Bin.valuation_rate)
        .where(Bin.item_code.isin(item_codes))
    )

    if filters.get("warehouse"):
        query = query.where(Bin.warehouse == filters.warehouse)

    return query.run(as_dict=True)


def build_bin_maps(bin_rows):
    qty_map = {}
    value_map = {}
    warehouse_map = {}

    for row in bin_rows:
        item_code = row.item_code
        actual_qty = flt(row.actual_qty)
        valuation_rate = flt(row.valuation_rate)

        qty_map[item_code] = flt(qty_map.get(item_code)) + actual_qty
        value_map[item_code] = flt(value_map.get(item_code)) + (
            actual_qty * valuation_rate
        )

        if item_code not in warehouse_map:
            warehouse_map[item_code] = []

        if actual_qty != 0:
            warehouse_map[item_code].append(row.warehouse + " - " + str(actual_qty))

    return qty_map, value_map, warehouse_map


def get_price_rows(item_codes, price_lists):
    if not item_codes or not price_lists:
        return []

    ItemPrice = frappe.qb.DocType("Item Price")

    return (
        frappe.qb.from_(ItemPrice)
        .select(
            ItemPrice.name,
            ItemPrice.item_code,
            ItemPrice.price_list,
            ItemPrice.price_list_rate,
            ItemPrice.uom,
            ItemPrice.valid_from,
            ItemPrice.valid_upto,
            ItemPrice.customer,
            ItemPrice.supplier,
            ItemPrice.batch_no,
            ItemPrice.modified,
        )
        .where(ItemPrice.item_code.isin(item_codes))
        .where(ItemPrice.price_list.isin(price_lists))
        .orderby(ItemPrice.modified)
        .run(as_dict=True)
    )


def build_price_map(price_rows, item_uom_map, as_on_date=None):
    price_map = {}
    as_on_date = getdate(as_on_date or today())

    for row in price_rows:
        if row.valid_from and getdate(row.valid_from) > as_on_date:
            continue

        if row.valid_upto and getdate(row.valid_upto) < as_on_date:
            continue

        if row.customer or row.supplier or row.batch_no:
            continue

        stock_uom = item_uom_map.get(row.item_code)
        if row.uom and stock_uom and row.uom != stock_uom:
            continue

        price_map[(row.item_code, row.price_list)] = flt(row.price_list_rate)

    return price_map


def build_data(
    items, price_lists, price_map, qty_map, value_map, warehouse_map, filters
):
    data = []
    tax_rate = flt(filters.get("tax_rate"))
    only_with_stock = bool(filters.get("only_with_stock"))
    only_with_price = bool(filters.get("only_with_price"))

    for item in items:
        total_qty = flt(qty_map.get(item.item_code))
        total_value = flt(value_map.get(item.item_code))
        valuation_rate = total_value / total_qty if total_qty else 0.0

        row_data = {
            "item_code": item.item_code,
            "description": item.description,
            "default_tax_template": item.get("default_tax_template"),
            "total_qty": total_qty,
            "last_purchase_rate": item.last_purchase_rate,
            "valuation_rate": valuation_rate,
            "warehouse_qty": "<br>".join(warehouse_map.get(item.item_code) or []),
        }

        has_price = False

        for price_list in price_lists:
            field_base = get_price_field_base(price_list.name)
            rate = flt(price_map.get((item.item_code, price_list.name)))

            if rate:
                has_price = True

            row_data[field_base] = rate
            row_data[field_base + "_excl"] = (
                rate / (1 + (tax_rate / 100)) if rate else 0.0
            )

        if only_with_stock and total_qty == 0:
            continue

        if only_with_price and not has_price:
            continue

        data.append(row_data)

    return data
