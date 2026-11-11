import frappe
from erpnext.controllers.trends import get_columns, get_data
from frappe.query_builder.functions import Concat, Sum
from frappe.utils import flt
from pypika.terms import CustomFunction
from csf_tz.utils.query_builder import GroupConcatWithSeparator

Format = CustomFunction("FORMAT", ["number", "decimals"])


def execute(filters=None):
	filters = filters or {}

	# Get standard columns and data
	result = get_columns(filters, "Sales Invoice")
	columns, data = result["columns"], get_data(filters, result)

	# Find the index of the item_code column
	item_idx = next((i for i, col in enumerate(columns)
	                 if isinstance(col, dict) and col.get("fieldname") in ("item_code", "item")), 0)

	# Fetch Bin summary with formatted qty
	bin_map = {
		d.item_code: [flt(d.total_qty, 2), d.warehouse_summary]
		for d in get_bin_summary()
	}

	# Add Bin info to each row
	for row in data:
		row += bin_map.get(row[item_idx], [0.00, ""])

	# Add columns for available qty and warehouse summary
	columns += [
		{
			"label": "Total Available Qty",
			"fieldname": "total_available_qty",
			"fieldtype": "Float",
			"precision": 2
		},
		{
			"label": "Warehouse",
			"fieldname": "warehouse",
			"fieldtype": "Data"
		},
	]

	return columns, data


def get_bin_summary():
	stock_bin = frappe.qb.DocType("Bin")
	return (
		frappe.qb.from_(stock_bin)
		.select(
			stock_bin.item_code,
			Sum(stock_bin.actual_qty).as_("total_qty"),
			GroupConcatWithSeparator(
				Concat(stock_bin.warehouse, ": ", Format(stock_bin.actual_qty, 2)), ", "
			).as_("warehouse_summary"),
		)
		.groupby(stock_bin.item_code)
		.run(as_dict=True)
	)
