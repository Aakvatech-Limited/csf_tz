# Copyright (c) 2019, Aakvatech and contributors
# For license information, please see license.txt

# ERPNext v15 moved get_item_details, get_item_warehouse_map, get_items and
# get_stock_ledger_entries into StockBalanceReport and removed the module-level
# exports; get_fifo_queue was removed from stock_ageing entirely. This report
# also imported `six`, which is not available in Python 3. The report needs a
# full rewrite against the v15 API before it can be used.

import frappe
from frappe import _


def execute(filters=None):
	frappe.throw(
		_(
			"Warehouse Wise Item Balance and Value has not been ported to ERPNext v15. "
			"Please contact your system administrator."
		)
	)
