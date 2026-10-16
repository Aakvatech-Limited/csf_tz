# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		filters = {}
	stock_ledger_entry = get_stock_ledger_entries(filters)
	if not stock_ledger_entry:
		return [], []

	columns, warehouses = get_columns(stock_ledger_entry)
	sle_warehouse_map = get_sle_warehouse_map(stock_ledger_entry)

	data = []
	for sle in stock_ledger_entry:
		row = [sle.item_code, sle.item_name, sle.brand, sle.item_group]

		warehouse_qty = [flt(sle_warehouse_map.get(sle.item_code, {}).get(e)) for e in warehouses]
		row += warehouse_qty + [sum(warehouse_qty)]

		data.append(row)

	return columns, data


def get_columns(stock_ledger_entry):
	columns = [
		_("Item Code") + ":Link/Item:150",
		_("Item") + ":Data/Item Name:150",
		_("Brand") + ":Link/Brand:150",
		_("Item Group") + ":Link/Item Group:150",
	]

	warehouses = {_("Warehouse"): []}

	stock_ledger = frappe.qb.DocType("Stock Ledger Entry")
	warehouses_found = (
		frappe.qb.from_(stock_ledger)
		.select(stock_ledger.warehouse)
		.distinct()
		.where(stock_ledger.actual_qty != 0)
		.where(stock_ledger.item_code.isin([d.item_code for d in stock_ledger_entry]))
	).run(as_dict=True)
	for warehouse in warehouses_found:
		warehouses[_("Warehouse")].append(warehouse.warehouse)

	columns = (
		columns + [(e + ":Float:120") for e in warehouses[_("Warehouse")]] + [_("Total Stock") + ":Float:120"]
	)

	# frappe.msgprint(warehouses[_("Warehouse")])

	return columns, warehouses[_("Warehouse")]


def get_stock_ledger_entries(filters):
	filters.update({"from_date": filters.get("from_date"), "to_date": filters.get("to_date")})
	conditions, filters = get_conditions(filters)
	stock_ledger = frappe.qb.DocType("Stock Ledger Entry")
	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(stock_ledger)
		.join(item).on(stock_ledger.item_code == item.item_code)
		.select(
			stock_ledger.item_code, item.item_name, item.brand, item.item_group,
			stock_ledger.warehouse, Sum(stock_ledger.actual_qty).as_("actual_qty"),
		)
		.groupby(stock_ledger.item_code, item.item_name, item.brand, item.item_group, stock_ledger.warehouse)
		.orderby(item.brand, item.item_group, stock_ledger.item_code)
	)
	if filters.get("from_date"):
		query = query.where(stock_ledger.posting_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(stock_ledger.posting_date <= filters["to_date"])
	if filters.get("item_group"):
		query = query.where(item.item_group == filters["item_group"])
	if filters.get("brand"):
		query = query.where(item.brand == filters["brand"])
	if filters.get("warehouse"):
		query = query.where(stock_ledger.warehouse == filters["warehouse"])
	stock_ledger_entry = query.run(as_dict=True)

	return stock_ledger_entry or []


def get_conditions(filters):
	conditions = ""

	if filters.get("from_date"):
		conditions += "posting_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " and posting_date <= %(to_date)s"
	if filters.get("item_group"):
		conditions += " and i.item_group = %(item_group)s"
	if filters.get("brand"):
		conditions += " and i.brand = %(brand)s"
	if filters.get("warehouse"):
		conditions += " and sle.warehouse = %(warehouse)s"

	return conditions, filters


def get_sle_warehouse_map(stock_ledger_entry):
	stock_ledger = frappe.qb.DocType("Stock Ledger Entry")
	item = frappe.qb.DocType("Item")
	sle_warehouses = (
		frappe.qb.from_(stock_ledger)
		.join(item).on(stock_ledger.item_code == item.item_code)
		.select(
			stock_ledger.item_code, stock_ledger.warehouse,
			Sum(stock_ledger.actual_qty).as_("actual_qty"),
		)
		.where(stock_ledger.item_code.isin([d.item_code for d in stock_ledger_entry]))
		.groupby(stock_ledger.item_code, stock_ledger.warehouse)
	).run(as_dict=True)

	sle_warehouse_map = {}
	for d in sle_warehouses:
		sle_warehouse_map.setdefault(d.item_code, frappe._dict()).setdefault(d.warehouse, [])
		# frappe.msgprint(d)
		sle_warehouse_map[d.item_code][d.warehouse] = flt(d.actual_qty)

	return sle_warehouse_map
