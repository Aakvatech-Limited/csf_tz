# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

import erpnext
import frappe
from erpnext.stock.utils import add_additional_uom_columns
from frappe import _
from frappe.utils import cint, flt, getdate
from six import iteritems

from csf_tz.csf_tz.report.excise_duty_stock.excise_duty_stock import (
	get_items,
	get_stock_ledger_entries_query,
)


def execute(filters=None):
	if not filters:
		filters = {}

	validate_filters(filters)

	if filters.get("company"):
		company_currency = erpnext.get_company_currency(filters.get("company"))
	else:
		company_currency = frappe.db.get_single_value("Global Defaults", "default_currency")

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
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100},
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
			"label": _("Balance Qty"),
			"fieldname": "bal_qty",
			"fieldtype": "Float",
			"width": 100,
			"convertible": "qty",
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
			{"label": att_name, "fieldname": att_name, "width": 100} for att_name in get_variants_attributes()
		]

	return columns


def get_stock_ledger_entries(filters, items):
	return get_stock_ledger_entries_query(filters, items).run(as_dict=True)


def get_item_warehouse_map(filters, sle):
	iwb_map = {}
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	for d in sle:
		key = (d.company, d.item_code)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict(
				{"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "excise_stock": 0.0, "bal_qty": 0.0}
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


def get_item_details(items, sle, filters):
	item_details = {}
	if not items:
		items = list({entry.item_code for entry in sle})
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
		conversion = frappe.qb.DocType("UOM Conversion Detail")
		query = (
			query.left_join(conversion)
			.on((conversion.parent == item.name) & (conversion.uom == filters["include_uom"]))
			.select(conversion.conversion_factor)
		)
	for row in query.run(as_dict=True):
		item_details.setdefault(row.name, row)

	if filters.get("show_variant_attributes", 0) == 1:
		variant_values = get_variant_values_for(list(item_details))
		for item_code, row in item_details.items():
			row.update(variant_values.get(item_code, {}))
	return item_details


def validate_filters(filters):
	if not (filters.get("item_code") or filters.get("warehouse")):
		sle_count = frappe.db.count("Stock Ledger Entry")
		if sle_count > 500000:
			frappe.throw(_("Please set filter based on Item or Warehouse due to a large amount of entries."))


def get_variants_attributes():
	"""Return all item variant attributes."""
	return [i.name for i in frappe.get_all("Item Attribute")]


def get_variant_values_for(items):
	"""Return variant attributes for the supplied item codes."""
	if not items:
		return {}
	attribute = frappe.qb.DocType("Item Variant Attribute")
	rows = (
		frappe.qb.from_(attribute)
		.select(attribute.parent, attribute.attribute, attribute.attribute_value)
		.where(attribute.parent.isin(items))
		.run(as_dict=True)
	)
	attribute_map = {}
	for row in rows:
		attribute_map.setdefault(row.parent, {})[row.attribute] = row.attribute_value
	return attribute_map
