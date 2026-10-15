# Copyright (c) 2019, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots, get_average_age
from erpnext.stock.report.stock_balance.stock_balance import StockBalanceReport
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		filters = {}

	validate_filters(filters)

	columns = get_columns(filters)
	warehouse_list = get_warehouse_list(filters)
	item_ageing = FIFOSlots(filters).generate()
	item_balance, item_value, item_groups = get_item_wise_balances(filters, warehouse_list)
	data = []

	for item, wh_balance in item_balance.items():
		if not item_ageing.get(item):
			continue

		row = [item, item_groups[item], sum(item_value[item])]

		fifo_queue = item_ageing[item]["fifo_queue"]
		average_age = 0.00
		if fifo_queue:
			average_age = get_average_age(fifo_queue, filters["to_date"])

		row += [average_age]

		bal_qty = [sum(qty) for qty in zip(*wh_balance, strict=False)]
		total_qty = sum(bal_qty)
		if len(warehouse_list) > 1:
			row += [total_qty]
		row += bal_qty

		if total_qty > 0 or not filters.get("filter_total_zero_qty"):
			data.append(row)

	add_warehouse_column(columns, warehouse_list)
	check_zero_total_qty(columns, data)
	return columns, data


def get_item_wise_balances(filters, warehouse_list):
	"""Group the ERPNext stock balance rows by item, one qty per warehouse column."""
	item_balance, item_value, item_groups = {}, {}, {}
	report = StockBalanceReport(frappe._dict(filters, include_zero_stock_items=1))
	_columns, balances = report.run()

	for entry in sorted(balances, key=lambda d: (d.item_code, d.warehouse)):
		row = [flt(entry.bal_qty) if wh.name == entry.warehouse else 0.00 for wh in warehouse_list]
		total_stock_value = (
			flt(entry.bal_val) if entry.warehouse in [wh.name for wh in warehouse_list] else 0.00
		)
		item_balance.setdefault(entry.item_code, []).append(row)
		item_value.setdefault(entry.item_code, []).append(total_stock_value)
		item_groups[entry.item_code] = entry.item_group

	return item_balance, item_value, item_groups


def get_columns(_filters):
	"""return columns"""

	columns = [
		_("Item") + ":Link/Item:100",
		_("Item Group") + "::100",
		_("Value") + ":Currency:120",
		_("Age") + ":Float:60",
	]
	return columns


def validate_filters(filters):
	if not (filters.get("item_code") or filters.get("warehouse")):
		sle_count = frappe.db.count("Stock Ledger Entry")
		if sle_count > 500000:
			frappe.throw(_("Please set filter based on Item or Warehouse"))
	if not filters.get("company"):
		filters["company"] = frappe.defaults.get_user_default("Company")


def get_warehouse_list(filters):
	from frappe.core.doctype.user_permission.user_permission import get_permitted_documents

	warehouse = frappe.qb.DocType("Warehouse")
	query = frappe.qb.from_(warehouse).select(warehouse.name).where(warehouse.is_group == 0)
	user_permitted_warehouse = get_permitted_documents("Warehouse")
	if user_permitted_warehouse:
		query = query.where(warehouse.name.isin(list(user_permitted_warehouse)))
	elif filters.get("warehouse"):
		query = query.where(warehouse.name == filters["warehouse"])

	return query.run(as_dict=True)


def add_warehouse_column(columns, warehouse_list):
	if len(warehouse_list) > 1:
		columns += [_("Total Qty") + ":Int:80"]

	for wh in warehouse_list:
		columns += [_(wh.name) + ":Int:100"]


def check_zero_total_qty(columns, data):
	"""Drop warehouse columns whose quantity is zero on every row."""
	zero_qty_columns = []
	for column_num in range(5, len(columns)):
		column_total = 0
		for row_num in range(0, len(data)):
			column_total += data[row_num][column_num]
		if column_total == 0:
			zero_qty_columns.append(column_num)

	if len(zero_qty_columns) > 0:
		index = 0
		for col_num in zero_qty_columns:
			for row in data:
				del row[col_num - index]
			del columns[col_num - index]
			index += 1
