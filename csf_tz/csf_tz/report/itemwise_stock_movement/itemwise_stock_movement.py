# Copyright (c) 2019, Aakvatech and contributors
# For license information, please see license.txt

import frappe
import pandas as pd
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from frappe import _
from frappe.query_builder import Case, Criterion, Order
from frappe.query_builder.functions import Sum
from frappe.utils import getdate
from pypika.analytics import RowNumber
from pypika.terms import ExistsCriterion


def execute(filters=None):
	columns = get_columns()
	items = get_items(filters)
	if items == []:
		return columns, []

	sle = frappe.qb.DocType("Stock Ledger Entry")
	conditions = get_conditions(sle, filters, items)

	sl_entries = get_opening_balance_entries(sle, filters, conditions)
	sl_entries += get_stock_ledger_entries(sle, filters, conditions)

	data = []
	if sl_entries:
		pvt = pd.pivot_table(
			pd.DataFrame.from_records(sl_entries),
			values="actual_qty",
			index=["posting_date", "Particulars"],
			columns="item_code",
			fill_value=0,
		)
		data = pvt.reset_index().values.tolist()
		columns += pvt.columns.values.tolist()

	return columns, data


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 95},
		{"label": _("Particulars"), "fieldname": "Particulars", "width": 110},
	]


def get_stock_ledger_entries(sle, filters, conditions):
	si = frappe.qb.DocType("Sales Invoice")
	dn = frappe.qb.DocType("Delivery Note")

	particulars = (
		Case()
		.when(sle.voucher_type == "Sales Invoice", si.customer)
		.when(sle.voucher_type == "Delivery Note", dn.customer)
		.else_(sle.voucher_type)
	)

	query = (
		frappe.qb.from_(sle)
		.left_join(si)
		.on((sle.voucher_no == si.name) & (sle.company == si.company))
		.left_join(dn)
		.on((sle.voucher_no == dn.name) & (sle.company == dn.company))
		.select(
			sle.posting_date,
			particulars.as_("Particulars"),
			sle.item_code,
			Sum(sle.actual_qty).as_("actual_qty"),
		)
		.where(sle.actual_qty != 0)
		.where(sle.posting_date[filters.get("from_date") : filters.get("to_date")])
		.where(Criterion.all(conditions))
		.groupby(sle.posting_date, particulars, sle.item_code)
		.orderby(sle.posting_date)
	)

	return query.run(as_dict=True)


def get_opening_balance_entries(sle, filters, conditions):
	"""Opening balance per item: qty_after_transaction of the last entry
	before from_date in each warehouse, summed across warehouses."""
	last_sle = (
		frappe.qb.from_(sle)
		.select(
			sle.item_code,
			sle.qty_after_transaction,
			RowNumber()
			.over(sle.item_code, sle.warehouse)
			.orderby(sle.posting_datetime, sle.creation, order=Order.desc)
			.as_("row_no"),
		)
		.where(sle.posting_date < filters.get("from_date"))
		.where(Criterion.all(conditions))
	).as_("last_sle")

	query = (
		frappe.qb.from_(last_sle)
		.select(last_sle.item_code, Sum(last_sle.qty_after_transaction).as_("actual_qty"))
		.where(last_sle.row_no == 1)
		.groupby(last_sle.item_code)
	)

	entries = query.run(as_dict=True)

	opening_date = getdate(filters.get("from_date"))
	for entry in entries:
		entry.posting_date = opening_date
		entry.Particulars = ". Opening Balance"

	return entries


def get_conditions(sle, filters, items):
	conditions = [sle.company == filters.get("company"), sle.is_cancelled == 0]

	if filters.get("warehouse"):
		warehouse = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=True)
		if not warehouse:
			frappe.throw(_("Warehouse {0} not found").format(filters.get("warehouse")))
		wh = frappe.qb.DocType("Warehouse")
		conditions.append(
			ExistsCriterion(
				frappe.qb.from_(wh)
				.select(wh.name)
				.where((wh.lft >= warehouse.lft) & (wh.rgt <= warehouse.rgt) & (sle.warehouse == wh.name))
			)
		)

	if items:
		conditions.append(sle.item_code.isin(items))

	return conditions


def get_items(filters):
	"""Item codes to restrict the report to. None means no restriction;
	an empty list means the item filters matched nothing."""
	if filters.get("item_code"):
		return [filters.get("item_code")]

	if not (filters.get("brand") or filters.get("item_group")):
		return None

	item = frappe.qb.DocType("Item")
	query = frappe.qb.from_(item).select(item.name)

	if filters.get("brand"):
		query = query.where(item.brand == filters.get("brand"))

	if filters.get("item_group"):
		condition = get_item_group_condition(filters.get("item_group"), item)
		if condition is None:
			frappe.throw(_("Item Group {0} not found").format(filters.get("item_group")))
		query = query.where(condition)

	return [row[0] for row in query.run()]
