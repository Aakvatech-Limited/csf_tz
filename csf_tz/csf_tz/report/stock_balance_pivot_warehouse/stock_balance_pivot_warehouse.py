# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import Criterion
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

	sle = frappe.qb.DocType("Stock Ledger Entry")
	for warehouse in (
		frappe.qb.from_(sle)
		.select(sle.warehouse)
		.distinct()
		.where((sle.actual_qty != 0) & sle.item_code.isin([d.item_code for d in stock_ledger_entry]))
		.run(as_dict=True)
	):
		warehouses[_("Warehouse")].append(warehouse.warehouse)

	columns = (
		columns + [(e + ":Float:120") for e in warehouses[_("Warehouse")]] + [_("Total Stock") + ":Float:120"]
	)

	# frappe.msgprint(warehouses[_("Warehouse")])

	return columns, warehouses[_("Warehouse")]


def get_stock_ledger_entries(filters):
	filters.update({"from_date": filters.get("from_date"), "to_date": filters.get("to_date")})
	sle = frappe.qb.DocType("Stock Ledger Entry")
	item = frappe.qb.DocType("Item")
	stock_ledger_entry = (
		frappe.qb.from_(sle)
		.inner_join(item)
		.on(sle.item_code == item.item_code)
		.select(
			sle.item_code,
			item.item_name,
			item.brand,
			item.item_group,
			sle.warehouse,
			Sum(sle.actual_qty).as_("sum(sle.actual_qty)"),
		)
		.where(Criterion.all(get_conditions(filters)))
		.groupby(item.item_name, item.brand, item.item_group, sle.warehouse)
		.orderby(item.brand, item.item_group, sle.item_code)
		.run(as_dict=True)
	)

	return stock_ledger_entry or []


def get_conditions(filters):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	item = frappe.qb.DocType("Item")
	conditions = []

	if filters.get("from_date"):
		conditions.append(sle.posting_date >= filters.get("from_date"))
	if filters.get("to_date"):
		conditions.append(sle.posting_date <= filters.get("to_date"))
	if filters.get("item_group"):
		conditions.append(item.item_group == filters.get("item_group"))
	if filters.get("brand"):
		conditions.append(item.brand == filters.get("brand"))
	if filters.get("warehouse"):
		conditions.append(sle.warehouse == filters.get("warehouse"))

	return conditions


def get_sle_warehouse_map(stock_ledger_entry):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	item = frappe.qb.DocType("Item")
	sle_warehouses = (
		frappe.qb.from_(sle)
		.inner_join(item)
		.on(sle.item_code == item.item_code)
		.select(sle.item_code, sle.warehouse, Sum(sle.actual_qty).as_("sum(actual_qty)"))
		.where(sle.item_code.isin([d.item_code for d in stock_ledger_entry]))
		.groupby(item.item_name, item.brand, item.item_group, sle.warehouse)
		.run(as_dict=True)
	)

	sle_warehouse_map = {}
	for d in sle_warehouses:
		sle_warehouse_map.setdefault(d.item_code, frappe._dict()).setdefault(d.warehouse, [])
		# frappe.msgprint(d)
		sle_warehouse_map[d.item_code][d.warehouse] = flt(d.actual_qty)

	return sle_warehouse_map
