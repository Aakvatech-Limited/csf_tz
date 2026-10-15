import frappe
from erpnext.controllers.trends import get_columns, get_data
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}

	# Get standard columns and data
	result = get_columns(filters, "Sales Invoice")
	columns, data = result["columns"], get_data(filters, result)

	# Find the index of the item_code column
	item_idx = next(
		(
			i
			for i, col in enumerate(columns)
			if isinstance(col, dict) and col.get("fieldname") in ("item_code", "item")
		),
		0,
	)

	# Fetch Bin summary with formatted qty
	bin = frappe.qb.DocType("Bin")
	# Fetch each warehouse's quantity once, then assemble the display summary in Python.
	bin_rows = frappe.qb.from_(bin).select(bin.item_code, bin.warehouse, bin.actual_qty).run(as_dict=True)
	bin_map = {}
	for stock in bin_rows:
		entry = bin_map.setdefault(stock.item_code, [0.0, []])
		entry[0] += flt(stock.actual_qty)
		entry[1].append(f"{stock.warehouse}: {flt(stock.actual_qty):,.2f}")
	bin_map = {
		item_code: [flt(total, 2), ", ".join(warehouses)]
		for item_code, (total, warehouses) in bin_map.items()
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
			"precision": 2,
		},
		{"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Data"},
	]

	return columns, data
