import frappe
from erpnext.controllers.trends import get_columns, get_data
from frappe.utils import flt

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
		for d in frappe.db.sql("""
			SELECT
				item_code,
				SUM(actual_qty) AS total_qty,
				GROUP_CONCAT(CONCAT(warehouse, ": ", FORMAT(actual_qty, 2)) SEPARATOR ", ") AS warehouse_summary
			FROM `tabBin`
			GROUP BY item_code
		""", as_dict=True)
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
