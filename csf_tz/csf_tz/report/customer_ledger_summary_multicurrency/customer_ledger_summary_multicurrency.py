# Copyright (c) 2013, Aakvatech Limited and contributors
# For license information, please see license.txt


import frappe
from frappe import _, scrub
from frappe.query_builder import Criterion, Tuple
from frappe.query_builder.functions import IfNull
from frappe.utils import getdate, nowdate
from csf_tz.csf_tz.report.customer_conditions import get_customer_conditions


class PartyLedgerSummaryReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')

	def run(self, args):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		self.filters.party_type = args.get("party_type")
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])

		self.get_gl_entries()
		self.get_return_invoices()
		self.get_party_adjustment_amounts()

		columns = self.get_columns()
		data = self.get_data()
		return columns, data

	def get_columns(self):
		columns = [{
			"label": _(self.filters.party_type),
			"fieldtype": "Link",
			"fieldname": "party",
			"options": self.filters.party_type,
			"width": 200
		}]

		if self.party_naming_by == "Naming Series":
			columns.append({
				"label": _(self.filters.party_type + "Name"),
				"fieldtype": "Data",
				"fieldname": "party_name",
				"width": 110
			})

		credit_or_debit_note = "Credit Note" if self.filters.party_type == "Customer" else "Debit Note"

		columns += [
			{
				"label": _("Opening Balance"),
				"fieldname": "opening_balance",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Invoiced Amount"),
				"fieldname": "invoiced_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Paid Amount"),
				"fieldname": "paid_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _(credit_or_debit_note),
				"fieldname": "return_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
		]

		for account in self.party_adjustment_accounts:
			columns.append({
				"label": account,
				"fieldname": "adj_" + scrub(account),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
				"is_adjustment": 1
			})

		columns += [
			{
				"label": _("Closing Balance"),
				"fieldname": "closing_balance",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Currency"),
				"fieldname": "currency",
				"fieldtype": "Link",
				"options": "Currency",
				"width": 50
			}
		]

		return columns

	def get_data(self):
		invoice_dr_or_cr = "debit_in_account_currency" if self.filters.party_type == "Customer" else "credit_in_account_currency"
		reverse_dr_or_cr = "credit_in_account_currency" if self.filters.party_type == "Customer" else "debit_in_account_currency"

		self.party_data = frappe._dict({})
		for gle in self.gl_entries:
			self.party_data.setdefault(gle.party, frappe._dict({
				"party": gle.party,
				"party_name": gle.party_name,
				"opening_balance": 0,
				"invoiced_amount": 0,
				"paid_amount": 0,
				"return_amount": 0,
				"closing_balance": 0,
				"currency": gle.account_currency
			}))

			amount = gle.get(invoice_dr_or_cr) - gle.get(reverse_dr_or_cr)
			self.party_data[gle.party].closing_balance += amount

			if gle.posting_date < self.filters.from_date or gle.is_opening == "Yes":
				self.party_data[gle.party].opening_balance += amount
			else:
				if amount > 0:
					self.party_data[gle.party].invoiced_amount += amount
				elif gle.voucher_no in self.return_invoices:
					self.party_data[gle.party].return_amount -= amount
				else:
					self.party_data[gle.party].paid_amount -= amount

		out = []
		for party, row in self.party_data.items():
			if row.opening_balance or row.invoiced_amount or row.paid_amount or row.return_amount or row.closing_amount:
				total_party_adjustment = sum(amount for amount in self.party_adjustment_details.get(party, {}).values())
				row.paid_amount -= total_party_adjustment

				adjustments = self.party_adjustment_details.get(party, {})
				for account in self.party_adjustment_accounts:
					row["adj_" + scrub(account)] = adjustments.get(account, 0)

				out.append(row)

		return out

	def get_gl_entries(self):
		gl_entry = frappe.qb.DocType("GL Entry")
		fields = [
			gl_entry.posting_date,
			gl_entry.party,
			gl_entry.voucher_type,
			gl_entry.voucher_no,
			gl_entry.against_voucher_type,
			gl_entry.against_voucher,
			gl_entry.debit,
			gl_entry.credit,
			gl_entry.is_opening,
			gl_entry.debit_in_account_currency,
			gl_entry.credit_in_account_currency,
			gl_entry.account_currency,
		]
		query = frappe.qb.from_(gl_entry)
		if self.filters.party_type in ("Customer", "Supplier"):
			party = frappe.qb.DocType(self.filters.party_type)
			party_name_field = "customer_name" if self.filters.party_type == "Customer" else "supplier_name"
			query = query.left_join(party).on(gl_entry.party == party.name)
			fields.append(party[party_name_field].as_("party_name"))

		query = (
			query.select(*fields)
			.where(
				(gl_entry.docstatus < 2)
				& (gl_entry.is_cancelled == 0)
				& (gl_entry.party_type == self.filters.party_type)
				& (IfNull(gl_entry.party, "") != "")
				& (gl_entry.posting_date <= self.filters.to_date)
			)
			.orderby(gl_entry.posting_date)
		)
		self.gl_entries = query.where(Criterion.all(self.prepare_conditions(gl_entry))).run(as_dict=True)

	def prepare_conditions(self, gl_entry):
		conditions = []

		if self.filters.company:
			conditions.append(gl_entry.company == self.filters.company)

		if self.filters.finance_book:
			conditions.append(IfNull(gl_entry.finance_book, "").isin([self.filters.finance_book, ""]))

		if self.filters.get("party"):
			conditions.append(gl_entry.party == self.filters.get("party"))

		if self.filters.party_type == "Customer":
			conditions += get_customer_conditions(self.filters, gl_entry)

		if self.filters.party_type == "Supplier" and self.filters.get("supplier_group"):
			supplier = frappe.qb.DocType("Supplier")
			conditions.append(
				gl_entry.party.isin(
					frappe.qb.from_(supplier)
					.select(supplier.name)
					.where(supplier.supplier_group == self.filters.get("supplier_group"))
				)
			)

		return conditions

	def get_return_invoices(self):
		doctype = "Sales Invoice" if self.filters.party_type == "Customer" else "Purchase Invoice"
		self.return_invoices = [d.name for d in frappe.get_all(doctype, filters={"is_return": 1, "docstatus": 1,
			"posting_date": ["between", [self.filters.from_date, self.filters.to_date]]})]

	def get_party_adjustment_amounts(self):
		income_or_expense = "Expense Account" if self.filters.party_type == "Customer" else "Income Account"
		invoice_dr_or_cr = "debit_in_account_currency" if self.filters.party_type == "Customer" else "credit_in_account_currency"
		reverse_dr_or_cr = "credit_in_account_currency" if self.filters.party_type == "Customer" else "debit_in_account_currency"
		round_off_account = frappe.get_cached_value('Company', self.filters.company, "round_off_account")

		gl_entry = frappe.qb.DocType("GL Entry")
		adjustment_gl_entry = frappe.qb.DocType("GL Entry", alias="adjustment_gle")
		party_gl_entry = frappe.qb.DocType("GL Entry", alias="party_gle")
		account = frappe.qb.DocType("Account")
		adjustment_vouchers = (
			frappe.qb.from_(adjustment_gl_entry)
			.join(account)
			.on(account.name == adjustment_gl_entry.account)
			.select(adjustment_gl_entry.voucher_type, adjustment_gl_entry.voucher_no)
			.where(
				(account.account_type == income_or_expense)
				& adjustment_gl_entry.posting_date.between(self.filters.from_date, self.filters.to_date)
				& (adjustment_gl_entry.docstatus < 2)
			)
		)
		party_vouchers = (
			frappe.qb.from_(party_gl_entry)
			.select(party_gl_entry.voucher_type, party_gl_entry.voucher_no)
			.where(
				(party_gl_entry.party_type == self.filters.party_type)
				& (IfNull(party_gl_entry.party, "") != "")
				& party_gl_entry.posting_date.between(self.filters.from_date, self.filters.to_date)
				& (party_gl_entry.docstatus < 2)
			)
		)
		party_vouchers = party_vouchers.where(Criterion.all(self.prepare_conditions(party_gl_entry)))

		voucher = Tuple(gl_entry.voucher_type, gl_entry.voucher_no)
		gl_entries = (
			frappe.qb.from_(gl_entry)
			.select(
				gl_entry.posting_date,
				gl_entry.account,
				gl_entry.party,
				gl_entry.voucher_type,
				gl_entry.voucher_no,
				gl_entry.debit_in_account_currency,
				gl_entry.credit_in_account_currency,
			)
			.where(
				(gl_entry.docstatus < 2)
				& (gl_entry.is_cancelled == 0)
				& voucher.isin(adjustment_vouchers)
				& voucher.isin(party_vouchers)
			)
		).run(as_dict=True)

		self.party_adjustment_details = {}
		self.party_adjustment_accounts = set()
		adjustment_voucher_entries = {}
		for gle in gl_entries:
			adjustment_voucher_entries.setdefault((gle.voucher_type, gle.voucher_no), [])
			adjustment_voucher_entries[(gle.voucher_type, gle.voucher_no)].append(gle)

		for voucher_gl_entries in adjustment_voucher_entries.values():
			parties = {}
			accounts = {}
			has_irrelevant_entry = False

			for gle in voucher_gl_entries:
				if gle.account == round_off_account:
					continue
				elif gle.party:
					parties.setdefault(gle.party, 0)
					parties[gle.party] += gle.get(reverse_dr_or_cr) - gle.get(invoice_dr_or_cr)
				elif frappe.get_cached_value("Account", gle.account, "account_type") == income_or_expense:
					accounts.setdefault(gle.account, 0)
					accounts[gle.account] += gle.get(invoice_dr_or_cr) - gle.get(reverse_dr_or_cr)
				else:
					has_irrelevant_entry = True

			if parties and accounts:
				if len(parties) == 1:
					party = list(parties.keys())[0]
					for account, amount in accounts.items():
						self.party_adjustment_accounts.add(account)
						self.party_adjustment_details.setdefault(party, {})
						self.party_adjustment_details[party].setdefault(account, 0)
						self.party_adjustment_details[party][account] += amount
				elif len(accounts) == 1 and not has_irrelevant_entry:
					account = list(accounts.keys())[0]
					self.party_adjustment_accounts.add(account)
					for party, amount in parties.items():
						self.party_adjustment_details.setdefault(party, {})
						self.party_adjustment_details[party].setdefault(account, 0)
						self.party_adjustment_details[party][account] += amount

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return PartyLedgerSummaryReport(filters).run(args)