# Copyright (c) 2021, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.utils import get_incoming_rate
from frappe import _, scrub
from frappe.query_builder import Order
from frappe.utils import cint, flt

from csf_tz import console
from csf_tz.utils.query_builder import get_match_criterion


def execute(filters=None):
	if not filters:
		filters = frappe._dict()
	filters.group_by = filters.get("group_by") or "Invoice"
	filters.currency = frappe.get_cached_value("Company", filters.company, "default_currency")

	gross_profit_data = GrossProfitGenerator(filters)

	data = []

	group_wise_columns = frappe._dict(
		{
			"invoice": [
				"parent",
				"customer",
				"customer_group",
				"posting_date",
				"item_code",
				"item_name",
				"item_group",
				"brand",
				"description",
				"warehouse",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
				"project",
			],
			"item_code": [
				"item_code",
				"item_name",
				"brand",
				"description",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"warehouse": [
				"warehouse",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"brand": [
				"brand",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"item_group": [
				"item_group",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"customer": [
				"customer",
				"customer_group",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"customer_group": [
				"customer_group",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"sales_person": [
				"sales_person",
				"allocated_amount",
				"qty",
				"base_rate",
				"buying_rate",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
			"project": ["project", "base_amount", "buying_amount", "gross_profit", "gross_profit_percent"],
			"territory": [
				"territory",
				"base_amount",
				"buying_amount",
				"gross_profit",
				"gross_profit_percent",
			],
		}
	)

	columns = get_columns(group_wise_columns, filters)

	for idx, src in enumerate(gross_profit_data.grouped_data):
		row = []
		for col in group_wise_columns.get(scrub(filters.group_by)):
			row.append(src.get(col))

		row.append(filters.currency)
		if idx == len(gross_profit_data.grouped_data) - 1:
			row[0] = frappe.bold("Total")
		data.append(row)

	return columns, data


def get_columns(group_wise_columns, filters):
	columns = []
	column_map = frappe._dict(
		{
			"parent": _("Sales Invoice") + ":Link/Sales Invoice:120",
			"posting_date": _("Posting Date") + ":Date:100",
			"posting_time": _("Posting Time") + ":Data:100",
			"item_code": _("Item Code") + ":Link/Item:100",
			"item_name": _("Item Name") + ":Data:100",
			"item_group": _("Item Group") + ":Link/Item Group:100",
			"brand": _("Brand") + ":Link/Brand:100",
			"description": _("Description") + ":Data:100",
			"warehouse": _("Warehouse") + ":Link/Warehouse:100",
			"qty": _("Qty") + ":Float:80",
			"base_rate": _("Avg. Selling Rate") + ":Currency/currency:100",
			"buying_rate": _("Valuation Rate") + ":Currency/currency:100",
			"base_amount": _("Selling Amount") + ":Currency/currency:100",
			"buying_amount": _("Buying Amount") + ":Currency/currency:100",
			"gross_profit": _("Gross Profit") + ":Currency/currency:100",
			"gross_profit_percent": _("Gross Profit %") + ":Percent:100",
			"project": _("Project") + ":Link/Project:100",
			"sales_person": _("Sales person"),
			"allocated_amount": _("Allocated Amount") + ":Currency/currency:100",
			"customer": _("Customer") + ":Link/Customer:100",
			"customer_group": _("Customer Group") + ":Link/Customer Group:100",
			"territory": _("Territory") + ":Link/Territory:100",
		}
	)

	for col in group_wise_columns.get(scrub(filters.group_by)):
		columns.append(column_map.get(col))

	columns.append(
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		}
	)

	return columns


class GrossProfitGenerator:
	def __init__(self, filters=None):
		self.data = []
		self.average_buying_rate = {}
		self.filters = frappe._dict(filters)
		self.load_invoice_items()
		self.load_stock_ledger_entries()
		self.load_product_bundle()
		self.load_non_stock_items()
		self.get_returned_invoice_items()
		self.process()

	def process(self):
		self.grouped = {}
		self.grouped_data = []

		self.currency_precision = cint(frappe.db.get_default("currency_precision")) or 3
		self.float_precision = cint(frappe.db.get_default("float_precision")) or 2

		for row in self.si_list:
			if self.skip_row(row, self.product_bundles):
				continue

			row.base_amount = flt(row.base_net_amount, self.currency_precision)

			product_bundles = []
			if row.update_stock:
				product_bundles = self.product_bundles.get(row.parenttype, {}).get(row.parent, frappe._dict())
			elif row.dn_detail:
				product_bundles = self.product_bundles.get("Delivery Note", {}).get(
					row.delivery_note, frappe._dict()
				)
				row.item_row = row.dn_detail

			# get buying amount
			if row.item_code in product_bundles:
				row.buying_amount = flt(
					self.get_buying_amount_from_product_bundle(row, product_bundles[row.item_code]),
					self.currency_precision,
				)
			else:
				row.buying_amount = flt(self.get_buying_amount(row, row.item_code), self.currency_precision)

			# get buying rate
			if row.qty:
				row.buying_rate = flt(row.buying_amount / row.qty, self.float_precision)
				row.base_rate = flt(row.base_amount / row.qty, self.float_precision)
			else:
				row.buying_rate, row.base_rate = 0.0, 0.0

			# calculate gross profit
			row.gross_profit = flt(row.base_amount - row.buying_amount, self.currency_precision)
			if row.base_amount:
				row.gross_profit_percent = flt(
					(row.gross_profit / row.base_amount) * 100.0, self.currency_precision
				)
			else:
				row.gross_profit_percent = 0.0

			# add to grouped
			self.grouped.setdefault(row.get(scrub(self.filters.group_by)), []).append(row)

		if self.grouped:
			self.get_average_rate_based_on_group_by()

	def get_average_rate_based_on_group_by(self):
		# sum buying / selling totals for group
		self.totals = frappe._dict(
			qty=0,
			base_amount=0,
			buying_amount=0,
			gross_profit=0,
			gross_profit_percent=0,
			base_rate=0,
			buying_rate=0,
		)
		for key in list(self.grouped):
			if self.filters.get("group_by") != "Invoice":
				for i, row in enumerate(self.grouped[key]):
					if i == 0:
						new_row = row
					else:
						new_row.qty += row.qty
						new_row.buying_amount += flt(row.buying_amount, self.currency_precision)
						new_row.base_amount += flt(row.base_amount, self.currency_precision)
				new_row = self.set_average_rate(new_row)
				self.grouped_data.append(new_row)
				self.add_to_totals(new_row)
			else:
				for _i, row in enumerate(self.grouped[key]):
					if (
						row.parent in self.returned_invoices
						and row.item_code in self.returned_invoices[row.parent]
					):
						returned_item_rows = self.returned_invoices[row.parent][row.item_code]
						for returned_item_row in returned_item_rows:
							row.qty += returned_item_row.qty
							row.base_amount += flt(returned_item_row.base_amount, self.currency_precision)
						row.buying_amount = flt(row.qty * row.buying_rate, self.currency_precision)
					if row.qty or row.base_amount:
						row = self.set_average_rate(row)
						self.grouped_data.append(row)
					self.add_to_totals(row)
		self.set_average_gross_profit(self.totals)
		self.grouped_data.append(self.totals)

	def set_average_rate(self, new_row):
		self.set_average_gross_profit(new_row)
		new_row.buying_rate = (
			flt(new_row.buying_amount / new_row.qty, self.float_precision) if new_row.qty else 0
		)
		new_row.base_rate = flt(new_row.base_amount / new_row.qty, self.float_precision) if new_row.qty else 0
		return new_row

	def set_average_gross_profit(self, new_row):
		new_row.gross_profit = flt(new_row.base_amount - new_row.buying_amount, self.currency_precision)
		new_row.gross_profit_percent = (
			flt(((new_row.gross_profit / new_row.base_amount) * 100.0), self.currency_precision)
			if new_row.base_amount
			else 0
		)

	def add_to_totals(self, new_row):
		for key in self.totals:
			if new_row.get(key):
				self.totals[key] += new_row[key]

	def get_returned_invoice_items(self):
		sales_invoice = frappe.qb.DocType("Sales Invoice")
		sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
		returned_invoices = (
			frappe.qb.from_(sales_invoice)
			.from_(sales_invoice_item)
			.select(
				sales_invoice.name,
				sales_invoice_item.item_code,
				sales_invoice_item.stock_qty.as_("qty"),
				sales_invoice_item.base_net_amount.as_("base_amount"),
				sales_invoice.return_against,
			)
			.where(sales_invoice.name == sales_invoice_item.parent)
			.where(sales_invoice.docstatus == 1)
			.where(sales_invoice.is_return == 1)
			.run(as_dict=True)
		)

		self.returned_invoices = frappe._dict()
		for inv in returned_invoices:
			self.returned_invoices.setdefault(inv.return_against, frappe._dict()).setdefault(
				inv.item_code, []
			).append(inv)

	def skip_row(self, row, product_bundles):
		if self.filters.get("group_by") != "Invoice":
			if not row.get(scrub(self.filters.get("group_by", ""))):
				return True
		elif row.get("is_return") == 1:
			return True

	def get_buying_amount_from_product_bundle(self, row, product_bundle):
		buying_amount = 0.0
		for packed_item in product_bundle:
			if packed_item.get("parent_detail_docname") == row.item_row:
				buying_amount += self.get_buying_amount(row, packed_item.item_code)

		return flt(buying_amount, self.currency_precision)

	def get_buying_amount(self, row, item_code):
		console("in buying amount", item_code)
		# IMP NOTE
		# stock_ledger_entries should already be filtered by item_code and warehouse and
		# sorted by posting_date desc, posting_time desc
		if item_code in self.non_stock_items and (row.project or row.cost_center):
			# Issue 6089-Get last purchasing rate for non-stock item
			item_rate = self.get_last_purchase_rate(item_code, row)
			console("non stock items item_rate", item_rate)

			return flt(row.qty) * item_rate

		else:
			my_sle = self.sle.get((item_code, row.warehouse))
			if (row.update_stock or row.dn_detail) and my_sle:
				parenttype, parent = row.parenttype, row.parent
				if row.dn_detail:
					parenttype, parent = "Delivery Note", row.delivery_note

				for i, sle in enumerate(my_sle):
					# find the stock valution rate from stock ledger entry
					if (
						sle.voucher_type == parenttype
						and parent == sle.voucher_no
						and sle.voucher_detail_no == row.item_row
					):
						previous_stock_value = len(my_sle) > i + 1 and flt(my_sle[i + 1].stock_value) or 0.0

						if previous_stock_value:
							return (
								(previous_stock_value - flt(sle.stock_value))
								* flt(row.qty)
								/ abs(flt(sle.qty))
							)
						else:
							return flt(row.qty) * self.get_average_buying_rate(row, item_code)
					else:
						console(
							"unknown criteria hit",
							sle.voucher_type,
							parenttype,
							parent,
							sle.voucher_no,
							sle.voucher_detail_no,
							row.item_row,
						)
			else:
				console("NO update stock or dn detail and no my_sel")
				return flt(row.qty) * self.get_average_buying_rate(row, item_code)

		console("0 returned as no matching code")
		return 0.0

	def get_average_buying_rate(self, row, item_code):
		args = row
		if item_code not in self.average_buying_rate:
			args.update(
				{
					"voucher_type": row.parenttype,
					"voucher_no": row.parent,
					"allow_zero_valuation": True,
					"company": self.filters.company,
				}
			)

			average_buying_rate = get_incoming_rate(args)
			self.average_buying_rate[item_code] = flt(average_buying_rate)

		return self.average_buying_rate[item_code]

	def get_last_purchase_rate(self, item_code, row):
		purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")
		query = (
			frappe.qb.from_(purchase_invoice_item)
			.select(purchase_invoice_item.base_rate / purchase_invoice_item.conversion_factor)
			.where(purchase_invoice_item.item_code == item_code)
			.where(purchase_invoice_item.docstatus == 1)
			.orderby(purchase_invoice_item.modified, order=Order.desc)
			.limit(1)
		)
		if row.project:
			query = query.where(purchase_invoice_item.project == row.project)
		elif row.cost_center:
			query = query.where(purchase_invoice_item.cost_center == row.cost_center)
		if self.filters.to_date:
			query = query.where(purchase_invoice_item.modified == self.filters.to_date)

		last_purchase_rate = query.run()

		return flt(last_purchase_rate[0][0]) if last_purchase_rate else 0

	def load_invoice_items(self):
		sales_invoice = frappe.qb.DocType("Sales Invoice")
		sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
		query = (
			frappe.qb.from_(sales_invoice)
			.inner_join(sales_invoice_item)
			.on(sales_invoice_item.parent == sales_invoice.name)
			.select(
				sales_invoice_item.parenttype,
				sales_invoice_item.parent,
				sales_invoice.posting_date,
				sales_invoice.posting_time,
				sales_invoice.project,
				sales_invoice.update_stock,
				sales_invoice.customer,
				sales_invoice.customer_group,
				sales_invoice.territory,
				sales_invoice_item.item_code,
				sales_invoice_item.item_name,
				sales_invoice_item.description,
				sales_invoice_item.warehouse,
				sales_invoice_item.item_group,
				sales_invoice_item.brand,
				sales_invoice_item.dn_detail,
				sales_invoice_item.delivery_note,
				sales_invoice_item.stock_qty.as_("qty"),
				sales_invoice_item.base_net_rate,
				sales_invoice_item.base_net_amount,
				sales_invoice_item.name.as_("item_row"),
				sales_invoice.is_return,
				sales_invoice_item.cost_center,
			)
			.where(sales_invoice.docstatus == 1)
			.where(sales_invoice.is_opening != "Yes")
			.orderby(sales_invoice.posting_date, order=Order.desc)
			.orderby(sales_invoice.posting_time, order=Order.desc)
		)

		if self.filters.group_by == "Sales Person":
			sales_team = frappe.qb.DocType("Sales Team")
			query = (
				query.left_join(sales_team)
				.on(sales_team.parent == sales_invoice.name)
				.select(sales_team.sales_person, sales_team.allocated_amount, sales_team.incentives)
			)

		if self.filters.company:
			query = query.where(sales_invoice.company == self.filters.company)
		if self.filters.from_date:
			query = query.where(sales_invoice.posting_date >= self.filters.from_date)
		if self.filters.to_date:
			query = query.where(sales_invoice.posting_date <= self.filters.to_date)
		if self.filters.get("sales_invoice"):
			query = query.where(sales_invoice.name == self.filters.sales_invoice)
		if self.filters.get("item_code"):
			query = query.where(sales_invoice_item.item_code == self.filters.item_code)
		if match_criterion := get_match_criterion("Sales Invoice"):
			query = query.where(match_criterion)

		self.si_list = query.run(as_dict=True)

	def load_stock_ledger_entries(self):
		stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
		res = (
			frappe.qb.from_(stock_ledger_entry)
			.select(
				stock_ledger_entry.item_code,
				stock_ledger_entry.voucher_type,
				stock_ledger_entry.voucher_no,
				stock_ledger_entry.voucher_detail_no,
				stock_ledger_entry.stock_value,
				stock_ledger_entry.warehouse,
				stock_ledger_entry.actual_qty.as_("qty"),
			)
			.where(stock_ledger_entry.company == self.filters.company)
			.where(stock_ledger_entry.is_cancelled == 0)
			.orderby(
				stock_ledger_entry.item_code,
				stock_ledger_entry.warehouse,
				stock_ledger_entry.posting_date,
				stock_ledger_entry.posting_time,
				stock_ledger_entry.creation,
				order=Order.desc,
			)
			.run(as_dict=True)
		)
		self.sle = {}
		for r in res:
			if (r.item_code, r.warehouse) not in self.sle:
				self.sle[(r.item_code, r.warehouse)] = []

			self.sle[(r.item_code, r.warehouse)].append(r)

	def load_product_bundle(self):
		self.product_bundles = {}

		packed_item = frappe.qb.DocType("Packed Item")
		for d in (
			frappe.qb.from_(packed_item)
			.select(
				packed_item.parenttype,
				packed_item.parent,
				packed_item.parent_item,
				packed_item.item_code,
				packed_item.warehouse,
				(-1 * packed_item.qty).as_("total_qty"),
				packed_item.parent_detail_docname,
			)
			.where(packed_item.docstatus == 1)
			.run(as_dict=True)
		):
			self.product_bundles.setdefault(d.parenttype, frappe._dict()).setdefault(
				d.parent, frappe._dict()
			).setdefault(d.parent_item, []).append(d)

	def load_non_stock_items(self):
		self.non_stock_items = frappe.get_all("Item", filters={"is_stock_item": 0}, pluck="name")
