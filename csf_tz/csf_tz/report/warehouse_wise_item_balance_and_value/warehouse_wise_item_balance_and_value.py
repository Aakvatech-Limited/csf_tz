# Copyright (c) 2019, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from erpnext.stock.report.stock_ageing.stock_ageing import get_average_age, get_fifo_queue
from erpnext.stock.report.stock_balance.stock_balance import (
	get_item_details,
	get_item_warehouse_map,
	get_items,
	get_stock_ledger_entries,
)
from frappe import _
from frappe.utils import flt
from six import iteritems


def execute(filters=None):
	if not filters:
		filters = {}

	validate_filters(filters)

	columns = get_columns(filters)

	items = get_items(filters)
	sle = get_stock_ledger_entries(filters, items)

	item_map = get_item_details(items, sle, filters)
	iwb_map = get_item_warehouse_map(filters, sle)
	warehouse_list = get_warehouse_list(filters)
	item_ageing = get_fifo_queue(filters)
	data = []
	item_balance = {}
	item_value = {}

	for company, item, warehouse in sorted(iwb_map):
		if not item_map.get(item):
			continue

		row = []
		qty_dict = iwb_map[(company, item, warehouse)]
		item_balance.setdefault((item, item_map[item]["item_group"]), [])
		total_stock_value = 0.00
		for wh in warehouse_list:
			row += [qty_dict.bal_qty] if wh.name in warehouse else [0.00]
			total_stock_value += qty_dict.bal_val if wh.name in warehouse else 0.00

		item_balance[(item, item_map[item]["item_group"])].append(row)
		item_value.setdefault((item, item_map[item]["item_group"]), [])
		item_value[(item, item_map[item]["item_group"])].append(total_stock_value)

	# sum bal_qty by item
	for (item, item_group), wh_balance in iteritems(item_balance):
		if not item_ageing.get(item):
			continue

		total_stock_value = sum(item_value[(item, item_group)])
		row = [item, item_group, total_stock_value]

		fifo_queue = item_ageing[item]["fifo_queue"]
		average_age = 0.00
		if fifo_queue:
			average_age = get_average_age(fifo_queue, filters["to_date"])

		row += [average_age]

		bal_qty = [sum(bal_qty) for bal_qty in zip(*wh_balance)]
		total_qty = sum(bal_qty)
		if len(warehouse_list) > 1:
			row += [total_qty]
		row += bal_qty

		if total_qty > 0:
			data.append(row)
		elif not filters.get("filter_total_zero_qty"):
			data.append(row)
	# frappe.msgprint("Debug start")
	# frappe.msgprint(str(data))
	add_warehouse_column(columns, warehouse_list)
	check_zero_total_qty(columns, data)
	# frappe.msgprint(str(columns) + " " + str(data))
	return columns, data


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
		sle_count = flt(frappe.db.sql("""select count(name) from `tabStock Ledger Entry`""")[0][0])
		if sle_count > 500000:
			frappe.throw(_("Please set filter based on Item or Warehouse"))
	if not filters.get("company"):
		filters["company"] = frappe.defaults.get_user_default("Company")


def get_warehouse_list(filters):
	from frappe.core.doctype.user_permission.user_permission import get_permitted_documents

	condition = ""
	user_permitted_warehouse = get_permitted_documents("Warehouse")
	value = ()
	if user_permitted_warehouse:
		condition = "and name in %s"
		value = set(user_permitted_warehouse)
	elif not user_permitted_warehouse and filters.get("warehouse"):
		condition = "and name = %s"
		value = filters.get("warehouse")

	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-sql-format-injection
	return frappe.db.sql(
		"""select name
		from `tabWarehouse` where is_group = 0
		{condition}""".format(condition=condition),
		value,
		as_dict=1,
	)


def add_warehouse_column(columns, warehouse_list):
	if len(warehouse_list) > 1:
		columns += [_("Total Qty") + ":Int:80"]

	for wh in warehouse_list:
		columns += [_(wh.name) + ":Int:100"]


def check_zero_total_qty(columns, data):
	zero_qty_columns = []
	# frappe.msgprint("Number of rows: " + str(len(data)) + " and number of columns " + str(len(columns)))
	for column_num in range(5, len(columns)):
		column_total = 0
		for row_num in range(0, len(data)):
			# frappe.msgprint("row " + str(row_num + 1) + " column " + str(column_num + 1) + " value" + str(data[row_num][column_num]))
			column_total += data[row_num][column_num]
		if column_total == 0:
			zero_qty_columns.append(column_num)
	# frappe.msgprint("These columns should be removed: " + str(zero_qty_columns))

	if len(zero_qty_columns) > 0:
		# frappe.msgprint("Total number of columns to be deleted: " + str(len(zero_qty_columns)))
		index = 0
		for col_num in zero_qty_columns:
			# frappe.msgprint("Deleting column " + str(col_num - index))
			for row in data:
				del row[col_num - index]
			del columns[col_num - index]
			index += 1
	# frappe.msgprint(str(columns) + " " + str(data))
