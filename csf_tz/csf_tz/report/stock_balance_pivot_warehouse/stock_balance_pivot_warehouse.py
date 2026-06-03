# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
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

		for e in warehouses:
			row.append(sle_warehouse_map.get(sle.item_code, {}).get(e))
		# row += [total_qty]

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

	for warehouse in frappe.db.sql(
		"""select distinct sle.warehouse
		from `tabStock Ledger Entry` sle
		where sle.actual_qty != 0 and sle.item_code in (%s)"""
		% (", ".join(["%s"] * len(stock_ledger_entry))),
		tuple([d.item_code for d in stock_ledger_entry]),
		as_dict=1,
	):
		warehouses[_("Warehouse")].append(warehouse.warehouse)

	columns = (
		columns + [(e + ":Float:120") for e in warehouses[_("Warehouse")]] + [_("Total Stock") + ":Float:120"]
	)

	# frappe.msgprint(warehouses[_("Warehouse")])

	return columns, warehouses[_("Warehouse")]


def get_stock_ledger_entries(filters):
	filters.update({"from_date": filters.get("from_date"), "to_date": filters.get("to_date")})
	conditions, filters = get_conditions(filters)
	stock_ledger_entry = frappe.db.sql(
		"""select sle.item_code, i.item_name, i.brand, i.item_group, sle.warehouse, sum(sle.actual_qty)
		from `tabStock Ledger Entry` sle
		inner join `tabItem` i on sle.item_code = i.item_code
		where %s
		group by i.item_name, i.brand, i.item_group, sle.warehouse
		order by i.brand, i.item_group, sle.item_code"""
		% conditions,
		filters,
		as_dict=1,
	)

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
	sle_warehouses = frappe.db.sql(
		"""select sle.item_code, sle.warehouse, sum(actual_qty)
		from `tabStock Ledger Entry` sle
		inner join `tabItem` i on sle.item_code = i.item_code
		where item_code in (%s)
		group by i.item_name, i.brand, i.item_group, sle.warehouse"""
		% (", ".join(["%s"] * len(stock_ledger_entry))),
		tuple([d.item_code for d in stock_ledger_entry]),
		as_dict=1,
	)

	sle_warehouse_map = {}
	for d in sle_warehouses:
		sle_warehouse_map.setdefault(d.item_code, frappe._dict()).setdefault(d.warehouse, [])
		# frappe.msgprint(d)
		sle_warehouse_map[d.item_code][d.warehouse] = flt(d.actual_qty)

	return sle_warehouse_map
