# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.query_builder import Criterion, Field
from frappe.query_builder.functions import Count
from frappe.utils import flt, cint, getdate
from erpnext.stock.utils import add_additional_uom_columns
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from pypika.terms import ExistsCriterion, ValueWrapper


from six import iteritems


def execute(filters=None):
    if not filters:
        filters = {}

    validate_filters(filters)

    if filters.get("company"):
        company_currency = erpnext.get_company_currency(filters.get("company"))
    else:
        company_currency = frappe.db.get_single_value(
            "Global Defaults", "default_currency"
        )

    include_uom = filters.get("include_uom")
    columns = get_columns(filters)
    items = get_items(filters)
    sle = get_stock_ledger_entries(filters, items)

    # if no stock ledger entry found return
    if not sle:
        return columns, []

    iwb_map = get_item_warehouse_map(filters, sle)
    item_map = get_item_details(items, sle, filters)

    data = []
    conversion_factors = {}

    def _func(x):
        return x[1]

    for company, item in sorted(iwb_map):
        if item_map.get(item):
            qty_dict = iwb_map[(company, item)]

            report_data = {
                "currency": company_currency,
                "item_code": item,
                "company": company,
            }
            report_data.update(item_map[item])
            report_data.update(qty_dict)

            if include_uom:
                conversion_factors.setdefault(item, item_map[item].conversion_factor)

            data.append(report_data)

    add_additional_uom_columns(columns, data, include_uom, conversion_factors)
    return columns, data


def get_columns(filters):
    """return columns"""
    columns = [
        {
            "label": _("Item"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 100,
        },
        {"label": _("Item Name"), "fieldname": "item_name", "width": 150},
        {
            "label": _("Item Group"),
            "fieldname": "item_group",
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 100,
        },
        {
            "label": _("Stock UOM"),
            "fieldname": "stock_uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 90,
        },
        {
            "label": _("Opening Qty"),
            "fieldname": "opening_qty",
            "fieldtype": "Float",
            "width": 100,
            "convertible": "qty",
        },
        {
            "label": _("In Qty"),
            "fieldname": "in_qty",
            "fieldtype": "Float",
            "width": 80,
            "convertible": "qty",
        },
        {
            "label": _("Out Qty"),
            "fieldname": "out_qty",
            "fieldtype": "Float",
            "width": 80,
            "convertible": "qty",
        },
        {
            "label": _("Balance Qty"),
            "fieldname": "bal_qty",
            "fieldtype": "Float",
            "width": 100,
            "convertible": "qty",
        },
        {
            "label": _("Excise Qty"),
            "fieldname": "excise_stock",
            "fieldtype": "Float",
            "width": 100,
            "convertible": "qty",
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 100,
        },
    ]

    if filters.get("show_variant_attributes"):
        columns += [
            {"label": att_name, "fieldname": att_name, "width": 100}
            for att_name in get_variants_attributes()
        ]

    return columns


def get_conditions(filters):
    sle = frappe.qb.DocType("Stock Ledger Entry")
    warehouse = frappe.qb.DocType("Warehouse")
    conditions = []
    if not filters.get("from_date"):
        frappe.throw(_("'From Date' is required"))

    if filters.get("to_date"):
        conditions.append(sle.posting_date <= filters.get("to_date"))
    else:
        frappe.throw(_("'To Date' is required"))

    if filters.get("company"):
        conditions.append(sle.company == filters.get("company"))

    if filters.get("warehouse"):
        warehouse_details = frappe.db.get_value(
            "Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1
        )
        if warehouse_details:
            conditions.append(
                ExistsCriterion(
                    frappe.qb.from_(warehouse)
                    .select(warehouse.name)
                    .where(
                        (warehouse.lft >= warehouse_details.lft)
                        & (warehouse.rgt <= warehouse_details.rgt)
                        & (sle.warehouse == warehouse.name)
                    )
                )
            )

    if filters.get("warehouse_type") and not filters.get("warehouse"):
        conditions.append(
            ExistsCriterion(
                frappe.qb.from_(warehouse)
                .select(warehouse.name)
                .where(
                    (warehouse.warehouse_type == filters.get("warehouse_type"))
                    & (sle.warehouse == warehouse.name)
                )
            )
        )

    return conditions


def get_stock_ledger_entries(filters, items):
    sle = frappe.qb.DocType("Stock Ledger Entry")
    stock_entry = frappe.qb.DocType("Stock Entry")
    sales_invoice = frappe.qb.DocType("Sales Invoice")
    conditions = get_conditions(filters)
    if items:
        conditions.append(sle.item_code.isin(items))

    stock_entry_query = get_excisable_entries_query(
        frappe.qb.from_(sle)
        .inner_join(stock_entry)
        .on((sle.voucher_type == "Stock Entry") & (stock_entry.name == sle.voucher_no)),
        ValueWrapper(0),
        conditions,
    ).where(stock_entry.purpose != "Material Transfer")
    sales_invoice_query = get_excisable_entries_query(
        frappe.qb.from_(sle)
        .inner_join(sales_invoice)
        .on((sle.voucher_type == "Sales Invoice") & (sales_invoice.name == sle.voucher_no)),
        sle.actual_qty * sales_invoice.excise_duty_applicable,
        conditions,
    )
    other_voucher_query = get_excisable_entries_query(
        frappe.qb.from_(sle), ValueWrapper(0), conditions
    ).where(sle.voucher_type.notin(["Stock Entry", "Sales Invoice"]))

    return (
        stock_entry_query.union_all(sales_invoice_query)
        .union_all(other_voucher_query)
        .orderby(Field("posting_date"))
        .run(as_dict=True)
    )


def get_excisable_entries_query(query, excise_stock, conditions):
    sle = frappe.qb.DocType("Stock Ledger Entry")
    item = frappe.qb.DocType("Item")
    return (
        query.inner_join(item)
        .on(sle.item_code == item.name)
        .select(
            sle.item_code,
            sle.warehouse,
            sle.posting_date,
            sle.actual_qty,
            sle.valuation_rate,
            sle.company,
            sle.voucher_type,
            sle.qty_after_transaction,
            sle.stock_value_difference,
            sle.item_code.as_("name"),
            sle.voucher_no,
            sle.stock_value,
            excise_stock.as_("excise_stock"),
        )
        .where((sle.is_cancelled == 0) & (item.excisable_item == 1) & (sle.docstatus < 2))
        .where(Criterion.all(conditions))
    )


def get_item_warehouse_map(filters, sle):
    iwb_map = {}
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))

    float_precision = cint(frappe.db.get_default("float_precision")) or 3

    for d in sle:
        key = (d.company, d.item_code)
        if key not in iwb_map:
            iwb_map[key] = frappe._dict(
                {
                    "opening_qty": 0.0,
                    "in_qty": 0.0,
                    "out_qty": 0.0,
                    "excise_stock": 0.0,
                    "bal_qty": 0.0,
                }
            )

        qty_dict = iwb_map[(d.company, d.item_code)]

        if d.voucher_type == "Stock Reconciliation":
            qty_diff = flt(d.qty_after_transaction) - flt(qty_dict.bal_qty)
        else:
            qty_diff = flt(d.actual_qty)

        if d.posting_date < from_date:
            qty_dict.opening_qty += qty_diff

        elif d.posting_date >= from_date and d.posting_date <= to_date:
            if flt(qty_diff, float_precision) >= 0:
                qty_dict.in_qty += qty_diff
            else:
                qty_dict.out_qty += abs(qty_diff)
            qty_dict.excise_stock += abs(d.excise_stock) or 0

        qty_dict.bal_qty += qty_diff

    iwb_map = filter_items_with_no_transactions(iwb_map, float_precision)

    return iwb_map


def filter_items_with_no_transactions(iwb_map, float_precision):
    for company, item in sorted(iwb_map):
        qty_dict = iwb_map[(company, item)]

        no_transactions = True
        for key, val in iteritems(qty_dict):
            val = flt(val, float_precision)
            qty_dict[key] = val
            if key != "val_rate" and val:
                no_transactions = False

        if no_transactions:
            iwb_map.pop((company, item))

    return iwb_map


def get_items(filters):
    item = frappe.qb.DocType("Item")
    conditions = []
    if filters.get("item_code"):
        conditions.append(item.name == filters.get("item_code"))
    else:
        if filters.get("item_group"):
            conditions.append(get_item_group_condition(filters.get("item_group"), item))

    items = []
    if conditions:
        items = (
            frappe.qb.from_(item)
            .select(item.name)
            .where(Criterion.all(conditions))
            .run(pluck=True)
        )
    return items


def get_item_details(items, sle, filters):
    item_details = {}
    if not items:
        items = list(set([d.item_code for d in sle]))

    if not items:
        return item_details

    item = frappe.qb.DocType("Item")
    query = (
        frappe.qb.from_(item)
        .select(
            item.name,
            item.item_name,
            item.description,
            item.item_group,
            item.brand,
            item.stock_uom,
        )
        .where(item.name.isin(items))
    )
    if filters.get("include_uom"):
        uom_conversion = frappe.qb.DocType("UOM Conversion Detail")
        query = (
            query.left_join(uom_conversion)
            .on(
                (uom_conversion.parent == item.name)
                & (uom_conversion.uom == filters.get("include_uom"))
            )
            .select(uom_conversion.conversion_factor)
        )
    res = query.run(as_dict=True)

    for item in res:
        item_details.setdefault(item.name, item)

    if filters.get("show_variant_attributes", 0) == 1:
        variant_values = get_variant_values_for(list(item_details))
        item_details = {
            k: v.update(variant_values.get(k, {})) for k, v in iteritems(item_details)
        }

    return item_details


def validate_filters(filters):
    if not (filters.get("item_code") or filters.get("warehouse")):
        sle = frappe.qb.DocType("Stock Ledger Entry")
        sle_count = flt(frappe.qb.from_(sle).select(Count(sle.name)).run()[0][0])
        if sle_count > 500000:
            frappe.throw(
                _(
                    "Please set filter based on Item or Warehouse due to a large amount of entries."
                )
            )


def get_variants_attributes():
    """Return all item variant attributes."""
    return [i.name for i in frappe.get_all("Item Attribute")]


def get_variant_values_for(items):
    """Returns variant values for items."""
    attribute_map = {}
    variant_attribute = frappe.qb.DocType("Item Variant Attribute")
    for attr in (
        frappe.qb.from_(variant_attribute)
        .select(
            variant_attribute.parent,
            variant_attribute.attribute,
            variant_attribute.attribute_value,
        )
        .where(variant_attribute.parent.isin(items))
        .run(as_dict=True)
    ):
        attribute_map.setdefault(attr["parent"], {})
        attribute_map[attr["parent"]].update(
            {attr["attribute"]: attr["attribute_value"]}
        )

    return attribute_map
