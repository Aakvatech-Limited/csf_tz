# Copyright (c) 2015, Frappe Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import getdate, nowdate, flt, cint, formatdate, cstr
from csf_tz.csf_tz.report.customer_conditions import get_customer_conditions
from csf_tz.utils.query_builder import GroupConcatWithSeparator

class ReceivablePayableReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.report_date = getdate(self.filters.report_date or nowdate())
		self.age_as_on = getdate(nowdate()) \
			if self.filters.report_date > getdate(nowdate()) \
			else self.filters.report_date

	def run(self, args):
		party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		columns = self.get_columns(party_naming_by, args)
		data = self.get_data(party_naming_by, args)
		chart = self.get_chart_data(columns, data)
		return columns, data, None, chart

	def get_columns(self, party_naming_by, args):
		columns = []
		columns.append({
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"fieldname": "posting_date",
			"width": 90
		})

		columns += [_(args.get("party_type")) + ":Link/" + args.get("party_type") + ":200"]

		if args.get("party_type") == 'Customer':
			columns.append({
				"label": _("Customer Contact"),
				"fieldtype": "Link",
				"fieldname": "contact",
				"options":"Contact",
				"width": 100
			})

		if party_naming_by == "Naming Series":
			columns += [args.get("party_type") + " Name::110"]

		columns.append({
			"label": _("Voucher Type"),
			"fieldtype": "Data",
			"fieldname": "voucher_type",
			"width": 110
		})

		columns.append({
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"fieldname": "voucher_no",
			"width": 110,
			"options": "voucher_type",
		})

		columns += [_("Due Date") + ":Date:80"]

		if args.get("party_type") == "Supplier":
			columns += [_("Bill No") + "::80", _("Bill Date") + ":Date:80"]

		credit_or_debit_note = "Credit Note" if args.get("party_type") == "Customer" else "Debit Note"

		if self.filters.based_on_payment_terms:
			columns.append({
				"label": _("Payment Term"),
				"fieldname": "payment_term",
				"fieldtype": "Data",
				"width": 120
			})
			columns.append({
				"label": _("Invoice Grand Total"),
				"fieldname": "invoice_grand_total",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			})

		for label in ("Invoiced Amount", "Paid Amount", credit_or_debit_note, "Outstanding Amount"):
			columns.append({
				"label": _(label),
				"fieldname": frappe.scrub(label),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			})

		columns += [_("Age (Days)") + ":Int:80"]

		self.ageing_col_idx_start = len(columns)

		if not "range1" in self.filters:
			self.filters["range1"] = "30"
		if not "range2" in self.filters:
			self.filters["range2"] = "60"
		if not "range3" in self.filters:
			self.filters["range3"] = "90"
		if not "range4" in self.filters:
			self.filters["range4"] = "120"

		for label in ("0-{range1}".format(range1=self.filters["range1"]),
			"{range1}-{range2}".format(range1=cint(self.filters["range1"])+ 1, range2=self.filters["range2"]),
			"{range2}-{range3}".format(range2=cint(self.filters["range2"])+ 1, range3=self.filters["range3"]),
			"{range3}-{range4}".format(range3=cint(self.filters["range3"])+ 1, range4=self.filters["range4"]),
			"{range4}-{above}".format(range4=cint(self.filters["range4"])+ 1, above=_("Above"))):
				columns.append({
					"label": label,
					"fieldname":label,
					"fieldtype": "Currency",
					"options": "currency",
					"width": 120
				})

		columns += [
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100
		},
		{
			"fieldname": "pdc/lc_ref",
			"label": _("PDC/LC Ref"),
			"fieldtype": "Data",
			"width": 110
		},
		{
			"fieldname": "pdc/lc_amount",
			"label": _("PDC/LC Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130
		},
		{
			"fieldname": "remaining_balance",
			"label": _("Remaining Balance"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130
		}]

		if args.get('party_type') == 'Customer':
			columns += [
				{
					"label": _("Customer LPO"),
					"fieldtype": "Data",
					"fieldname": "po_no",
					"width": 100,
				},
				_("Delivery Note") + ":Data:100",
				_("Territory") + ":Link/Territory:80",
				_("Customer Group") + ":Link/Customer Group:120",
				{
					"label": _("Sales Person"),
					"fieldtype": "Data",
					"fieldname": "sales_person",
					"width": 120,
				}
			]
		if args.get("party_type") == "Supplier":
			columns += [_("Supplier Group") + ":Link/Supplier Group:80"]

		columns.append(_("Remarks") + "::200")

		return columns

	def get_data(self, party_naming_by, args):
		from erpnext.accounts.utils import get_currency_precision
		self.currency_precision = get_currency_precision() or 2
		self.dr_or_cr = "debit" if args.get("party_type") == "Customer" else "credit"

		future_vouchers = self.get_entries_after(self.filters.report_date, args.get("party_type"))

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')

		self.company_currency = frappe.get_cached_value('Company',  self.filters.get("company"), "default_currency")

		return_entries = self.get_return_entries(args.get("party_type"))

		data = []
		self.pdc_details = get_pdc_details(args.get("party_type"), self.filters.report_date)
		gl_entries_data = self.get_entries_till(self.filters.report_date, args.get("party_type"))

		if gl_entries_data:
			voucher_nos = [d.voucher_no for d in gl_entries_data] or []
			dn_details = get_dn_details(args.get("party_type"), voucher_nos)
			self.voucher_details = get_voucher_details(args.get("party_type"), voucher_nos, dn_details)

		if self.filters.based_on_payment_terms and gl_entries_data:
			self.payment_term_map = self.get_payment_term_detail(voucher_nos)

		for gle in gl_entries_data:
			if self.is_receivable_or_payable(gle, self.dr_or_cr, future_vouchers, return_entries):
				outstanding_amount, credit_note_amount, payment_amount = self.get_outstanding_amount(
					gle,self.filters.report_date, self.dr_or_cr, return_entries)
				temp_outstanding_amt = outstanding_amount
				temp_credit_note_amt = credit_note_amount

				if abs(outstanding_amount) > 0.1/10**self.currency_precision:
					if self.filters.based_on_payment_terms and self.payment_term_map.get(gle.voucher_no):
						for d in self.payment_term_map.get(gle.voucher_no):
							# Allocate payment amount based on payment terms(FIFO order)
							payment_amount, d.payment_amount = self.allocate_based_on_fifo(payment_amount, d.payment_term_amount)

							term_outstanding_amount = d.payment_term_amount - d.payment_amount

							# Allocate credit note based on payment terms(FIFO order)
							credit_note_amount, d.credit_note_amount = self.allocate_based_on_fifo(credit_note_amount, term_outstanding_amount)

							term_outstanding_amount -= d.credit_note_amount

							row_outstanding = term_outstanding_amount
							# Allocate PDC based on payment terms(FIFO order)
							d.pdc_details, d.pdc_amount = self.allocate_pdc_amount_in_fifo(gle, row_outstanding)

							if term_outstanding_amount > 0:
								row = self.prepare_row(party_naming_by, args, gle, term_outstanding_amount,
									d.credit_note_amount, d.due_date, d.payment_amount , d.payment_term_amount,
									d.description, d.pdc_amount, d.pdc_details)
								data.append(row)

						if credit_note_amount:
							row = self.prepare_row_without_payment_terms(party_naming_by, args, gle, temp_outstanding_amt,
								temp_credit_note_amt)
							data.append(row)

					else:
						row = self.prepare_row_without_payment_terms(party_naming_by, args, gle, outstanding_amount,
							credit_note_amount)
						data.append(row)
		return data

	def allocate_pdc_amount_in_fifo(self, gle, row_outstanding):
		pdc_list = self.pdc_details.get((gle.voucher_no, gle.party), [])

		pdc_details = []
		pdc_amount = 0
		for pdc in pdc_list:
			if row_outstanding <= pdc.pdc_amount:
				pdc_amount += row_outstanding
				pdc.pdc_amount -= row_outstanding
				if row_outstanding and pdc.pdc_ref and pdc.pdc_date:
					pdc_details.append(cstr(pdc.pdc_ref) + "/" + formatdate(pdc.pdc_date))
				row_outstanding = 0

			else:
				pdc_amount = pdc.pdc_amount
				if pdc.pdc_amount and pdc.pdc_ref and pdc.pdc_date:
					pdc_details.append(cstr(pdc.pdc_ref) + "/" + formatdate(pdc.pdc_date))
				pdc.pdc_amount = 0
				row_outstanding -= pdc_amount

		return pdc_details, pdc_amount

	def prepare_row_without_payment_terms(self, party_naming_by, args, gle, outstanding_amount, credit_note_amount):
		pdc_list = self.pdc_details.get((gle.voucher_no, gle.party), [])
		pdc_amount = 0
		pdc_details = []
		for d in pdc_list:
			pdc_amount += flt(d.pdc_amount)
			if pdc_amount and d.pdc_ref and d.pdc_date:
				pdc_details.append(cstr(d.pdc_ref) + "/" + formatdate(d.pdc_date))

		row = self.prepare_row(party_naming_by, args, gle, outstanding_amount,
			credit_note_amount, pdc_amount=pdc_amount, pdc_details=pdc_details)

		return row


	@staticmethod
	def allocate_based_on_fifo(total_amount, row_amount):
		allocated_amount = 0
		if row_amount <= total_amount:
			allocated_amount = row_amount
			total_amount -= row_amount
		else:
			allocated_amount = total_amount
			total_amount = 0

		return total_amount, allocated_amount

	def prepare_row(self, party_naming_by, args, gle, outstanding_amount, credit_note_amount,
		due_date=None, paid_amt=None, payment_term_amount=None, payment_term=None, pdc_amount=None, pdc_details=None):
		row = [gle.posting_date, gle.party]

		# customer / supplier name
		if party_naming_by == "Naming Series":
			row += [self.get_party_name(gle.party_type, gle.party)]

		if args.get("party_type") == 'Customer':
			row += [self.get_customer_contact(gle.party_type, gle.party)]

		# get due date
		if not due_date:
			due_date = self.voucher_details.get(gle.voucher_no, {}).get("due_date", "")
		bill_date = self.voucher_details.get(gle.voucher_no, {}).get("bill_date", "")

		row += [gle.voucher_type, gle.voucher_no, due_date]

		# get supplier bill details
		if args.get("party_type") == "Supplier":
			row += [
				self.voucher_details.get(gle.voucher_no, {}).get("bill_no", ""),
				self.voucher_details.get(gle.voucher_no, {}).get("bill_date", "")
			]

		# invoiced and paid amounts
		invoiced_amount = gle.get(self.dr_or_cr) if (gle.get(self.dr_or_cr) > 0) else 0

		if self.filters.based_on_payment_terms:
			row+=[payment_term, invoiced_amount]
			if payment_term_amount:
				invoiced_amount = payment_term_amount

		if not payment_term_amount:
			paid_amt = invoiced_amount - outstanding_amount - credit_note_amount
		row += [invoiced_amount, paid_amt, credit_note_amount, outstanding_amount]

		# ageing data
		if self.filters.ageing_based_on == "Due Date":
			entry_date = due_date
		elif self.filters.ageing_based_on == "Supplier Invoice Date":
			entry_date = bill_date
		else:
			entry_date = gle.posting_date

		row += get_ageing_data(cint(self.filters.range1), cint(self.filters.range2),
			cint(self.filters.range3), cint(self.filters.range4), self.age_as_on, entry_date, outstanding_amount)

		# issue 6371-Ageing buckets should not have amounts if due date is not reached
		if self.filters.ageing_based_on == "Due Date" \
				and getdate(due_date) > getdate(self.filters.report_date):
			row[-1]=row[-2]=row[-3]=row[-4]=row[-5]=0

		if self.filters.ageing_based_on == "Supplier Invoice Date" \
				and getdate(bill_date) > getdate(self.filters.report_date):

			row[-1]=row[-2]=row[-3]=row[-4]=row[-5]=0

		if self.filters.get(scrub(args.get("party_type"))):
			row.append(gle.account_currency)
		else:
			row.append(self.company_currency)

		remaining_balance = outstanding_amount - flt(pdc_amount)
		pdc_details = ", ".join(pdc_details)
		row += [pdc_details, pdc_amount, remaining_balance]

		if args.get('party_type') == 'Customer':
			# customer LPO
			row += [self.voucher_details.get(gle.voucher_no, {}).get("po_no")]

			# Delivery Note
			row += [self.voucher_details.get(gle.voucher_no, {}).get("delivery_note")]

		# customer territory / supplier group
		if args.get("party_type") == "Customer":
			row += [self.get_territory(gle.party), self.get_customer_group(gle.party),
				self.voucher_details.get(gle.voucher_no, {}).get("sales_person")]
		if args.get("party_type") == "Supplier":
			row += [self.get_supplier_group(gle.party)]

		row.append(gle.remarks)

		return row

	def get_entries_after(self, report_date, party_type):
		# returns a distinct list
		return list(set([(e.voucher_type, e.voucher_no) for e in self.get_gl_entries(party_type, report_date, for_future=True)]))

	def get_entries_till(self, report_date, party_type):
		# returns a generator
		return self.get_gl_entries(party_type, report_date)

	@staticmethod
	def is_receivable_or_payable(gle, dr_or_cr, future_vouchers, return_entries):
		return (
			# advance
			(not gle.against_voucher) or

			# against sales order/purchase order
			(gle.against_voucher_type in ["Sales Order", "Purchase Order"]) or

			# sales invoice/purchase invoice
			(gle.against_voucher==gle.voucher_no and gle.get(dr_or_cr) > 0) or

			# standalone credit notes
			(gle.against_voucher==gle.voucher_no and gle.voucher_no in return_entries and not return_entries.get(gle.voucher_no)) or

			# entries adjusted with future vouchers
			((gle.against_voucher_type, gle.against_voucher) in future_vouchers)
		)

	@staticmethod
	def get_return_entries(party_type):
		doctype = "Sales Invoice" if party_type=="Customer" else "Purchase Invoice"
		return_entries = frappe._dict(frappe.get_all(doctype,
			filters={"is_return": 1, "docstatus": 1}, fields=["name", "return_against"], as_list=1))
		return return_entries

	def get_outstanding_amount(self, gle, report_date, dr_or_cr, return_entries):
		payment_amount, credit_note_amount = 0.0, 0.0
		reverse_dr_or_cr = "credit" if dr_or_cr=="debit" else "debit"
		for e in self.get_gl_entries_for(gle.party, gle.party_type, gle.voucher_type, gle.voucher_no):
			if getdate(e.posting_date) <= report_date \
				and (e.name!=gle.name or (e.voucher_no in return_entries and not return_entries.get(e.voucher_no))):

				amount = flt(e.get(reverse_dr_or_cr), self.currency_precision) - flt(e.get(dr_or_cr), self.currency_precision)
				if e.voucher_no not in return_entries:
					payment_amount += amount
				else:
					credit_note_amount += amount

		voucher_amount = flt(gle.get(dr_or_cr), self.currency_precision) - flt(gle.get(reverse_dr_or_cr), self.currency_precision)
		if gle.voucher_no in return_entries and not return_entries.get(gle.voucher_no):
			voucher_amount = 0

		outstanding_amount = flt((voucher_amount - payment_amount - credit_note_amount), self.currency_precision)
		credit_note_amount = flt(credit_note_amount, self.currency_precision)

		return outstanding_amount, credit_note_amount, payment_amount

	def get_party_name(self, party_type, party_name):
		return self.get_party_map(party_type).get(party_name, {}).get("customer_name" if party_type == "Customer" else "supplier_name") or ""

	def get_customer_contact(self, party_type, party_name):
		return self.get_party_map(party_type).get(party_name, {}).get("customer_primary_contact")

	def get_territory(self, party_name):
		return self.get_party_map("Customer").get(party_name, {}).get("territory") or ""

	def get_customer_group(self, party_name):
		return self.get_party_map("Customer").get(party_name, {}).get("customer_group") or ""

	def get_supplier_group(self, party_name):
		return self.get_party_map("Supplier").get(party_name, {}).get("supplier_group") or ""

	def get_party_map(self, party_type):
		if not hasattr(self, "party_map"):
			party = frappe.qb.DocType(party_type)
			if party_type == "Customer":
				select_fields = [party.name, party.customer_name, party.territory, party.customer_group, party.customer_primary_contact]
			elif party_type == "Supplier":
				select_fields = [party.name, party.supplier_name, party.supplier_group]

			self.party_map = dict(((r.name, r) for r in frappe.qb.from_(party).select(*select_fields).run(as_dict=True)))

		return self.party_map

	def get_gl_entries(self, party_type, date=None, for_future=False):
		gl_entry = frappe.qb.DocType("GL Entry")
		conditions = self.prepare_conditions(party_type, gl_entry)

		if self.filters.get(scrub(party_type)):
			amount_fields = [
				Sum(gl_entry.debit_in_account_currency).as_("debit"),
				Sum(gl_entry.credit_in_account_currency).as_("credit"),
			]
		else:
			amount_fields = [Sum(gl_entry.debit).as_("debit"), Sum(gl_entry.credit).as_("credit")]

		if date and not for_future:
			conditions.append(gl_entry.posting_date <= date)

		if date and for_future:
			conditions.append(gl_entry.posting_date > date)

		query = (
			frappe.qb.from_(gl_entry)
			.select(
				gl_entry.name,
				gl_entry.posting_date,
				gl_entry.account,
				gl_entry.party_type,
				gl_entry.party,
				gl_entry.voucher_type,
				gl_entry.voucher_no,
				gl_entry.against_voucher_type,
				gl_entry.against_voucher,
				gl_entry.account_currency,
				gl_entry.remarks,
				*amount_fields,
			)
			.where(
				(gl_entry.docstatus < 2)
				& (gl_entry.party_type == party_type)
				& (gl_entry.party.isnotnull() & (gl_entry.party != ""))
			)
			.groupby(
				gl_entry.voucher_type,
				gl_entry.voucher_no,
				gl_entry.against_voucher_type,
				gl_entry.against_voucher,
				gl_entry.party,
			)
			.orderby(gl_entry.posting_date)
			.orderby(gl_entry.party)
		)
		self.gl_entries = query.where(Criterion.all(conditions)).run(as_dict=True)

		return self.gl_entries

	def prepare_conditions(self, party_type, gl_entry):
		conditions = []

		party_type_field = scrub(party_type)

		if self.filters.company:
			conditions.append(gl_entry.company == self.filters.company)

		if self.filters.finance_book:
			conditions.append(IfNull(gl_entry.finance_book, "").isin([self.filters.finance_book, ""]))

		if self.filters.get(party_type_field):
			conditions.append(gl_entry.party == self.filters.get(party_type_field))

		if party_type_field=="customer":
			account_type = "Receivable"
			conditions += get_customer_conditions(self.filters, gl_entry)

		elif party_type_field=="supplier":
			account_type = "Payable"
			if self.filters.get("supplier_group"):
				supplier = frappe.qb.DocType("Supplier")
				conditions.append(gl_entry.party.isin(
					frappe.qb.from_(supplier)
					.select(supplier.name)
					.where(supplier.supplier_group == self.filters.get("supplier_group"))
				))

		accounts = [d.name for d in frappe.get_all("Account",
			filters={"account_type": account_type, "company": self.filters.company})]
		conditions.append(gl_entry.account.isin(accounts))

		return conditions

	def get_gl_entries_for(self, party, party_type, against_voucher_type, against_voucher):
		if not hasattr(self, "gl_entries_map"):
			self.gl_entries_map = {}
			for gle in self.get_gl_entries(party_type):
				if gle.against_voucher_type and gle.against_voucher:
					self.gl_entries_map.setdefault(gle.party, {})\
						.setdefault(gle.against_voucher_type, {})\
						.setdefault(gle.against_voucher, [])\
						.append(gle)

		return self.gl_entries_map.get(party, {})\
			.get(against_voucher_type, {})\
			.get(against_voucher, [])

	def get_payment_term_detail(self, voucher_nos):
		payment_term_map = frappe._dict()
		payment_terms_details = frappe.db.sql(""" select si.name,
			party_account_currency, currency, si.conversion_rate,
			ps.due_date, ps.payment_amount, ps.description
			from `tabSales Invoice` si, `tabPayment Schedule` ps
			where si.name = ps.parent and
			si.docstatus = 1 and si.company = '%s' and
			si.name in (%s) order by ps.due_date
		"""	% (frappe.db.escape(self.filters.company), ','.join(['%s'] *len(voucher_nos))),
		(tuple(voucher_nos)), as_dict = 1)

		for d in payment_terms_details:
			payment_term_amount = d.payment_amount

			payment_term_map.setdefault(d.name, []).append(frappe._dict({
				"due_date": d.due_date,
				"payment_term_amount": payment_term_amount,
				"description": d.description
			}))
		return payment_term_map

	def get_chart_data(self, columns, data):
		ageing_columns = columns[self.ageing_col_idx_start : self.ageing_col_idx_start+5]

		rows = []
		for d in data:
			rows.append(
				{
					'values': d[self.ageing_col_idx_start : self.ageing_col_idx_start+5]
				}
			)

		return {
			"data": {
				'labels': [d.get("label") for d in ageing_columns],
				'datasets': rows
			},
			"type": 'percentage'
		}

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return ReceivablePayableReport(filters).run(args)

def get_ageing_data(first_range, second_range, third_range,
	fourth_range, age_as_on, entry_date, outstanding_amount):
	# [0-30, 30-60, 60-90, 90-120, 120-above]
	outstanding_range = [0.0, 0.0, 0.0, 0.0, 0.0]

	if not (age_as_on and entry_date):
		return [0] + outstanding_range

	age = (getdate(age_as_on) - getdate(entry_date)).days or 0
	index = None
	for i, days in enumerate([first_range, second_range, third_range, fourth_range]):
		if age <= days:
			index = i
			break

	if index is None: index = 4
	outstanding_range[index] = outstanding_amount

	return [age] + outstanding_range

def get_pdc_details(party_type, report_date):
	pdc_details = frappe._dict()
	payment_entry = frappe.qb.DocType("Payment Entry")
	payment_entry_reference = frappe.qb.DocType("Payment Entry Reference")
	pdc_via_pe = (
		frappe.qb.from_(payment_entry)
		.inner_join(payment_entry_reference)
		.on(payment_entry_reference.parent == payment_entry.name)
		.select(
			payment_entry_reference.reference_name.as_("invoice_no"),
			payment_entry.party,
			payment_entry.party_type,
			payment_entry.posting_date.as_("pdc_date"),
			IfNull(payment_entry_reference.allocated_amount, 0).as_("pdc_amount"),
			payment_entry.reference_no.as_("pdc_ref"),
		)
		.where(
			(payment_entry.docstatus < 2)
			& (payment_entry.posting_date > report_date)
			& (payment_entry.party_type == party_type)
		)
	).run(as_dict=True)

	for pdc in pdc_via_pe:
			pdc_details.setdefault((pdc.invoice_no, pdc.party), []).append(pdc)

	journal_entry = frappe.qb.DocType("Journal Entry")
	journal_entry_account = frappe.qb.DocType("Journal Entry Account")
	if scrub(party_type):
		amount_field = (journal_entry_account.debit_in_account_currency
			if party_type == 'Supplier' else journal_entry_account.credit_in_account_currency)
	else:
		amount_field = journal_entry_account.debit + journal_entry_account.credit

	pdc_via_je = (
		frappe.qb.from_(journal_entry)
		.inner_join(journal_entry_account)
		.on(journal_entry_account.parent == journal_entry.name)
		.select(
			journal_entry_account.reference_name.as_("invoice_no"),
			journal_entry_account.party,
			journal_entry_account.party_type,
			journal_entry.posting_date.as_("pdc_date"),
			IfNull(amount_field, 0).as_("pdc_amount"),
			journal_entry.cheque_no.as_("pdc_ref"),
		)
		.where(
			(journal_entry.docstatus < 2)
			& (journal_entry.posting_date > report_date)
			& (journal_entry_account.party_type == party_type)
		)
	).run(as_dict=True)

	for pdc in pdc_via_je:
		pdc_details.setdefault((pdc.invoice_no, pdc.party), []).append(pdc)

	return pdc_details

def get_dn_details(party_type, voucher_nos):
	dn_details = frappe._dict()

	if party_type == "Customer":
		sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
		for si in (
			frappe.qb.from_(sales_invoice_item)
			.select(
				sales_invoice_item.parent,
				GroupConcatWithSeparator(sales_invoice_item.delivery_note, ", ").as_("dn"),
			)
			.where(
				(sales_invoice_item.docstatus == 1)
				& sales_invoice_item.delivery_note.isnotnull()
				& (sales_invoice_item.delivery_note != "")
				& sales_invoice_item.parent.isin(voucher_nos)
			)
			.groupby(sales_invoice_item.parent)
		).run(as_dict=True):
			dn_details.setdefault(si.parent, si.dn)

		delivery_note_item = frappe.qb.DocType("Delivery Note Item")
		for si in (
			frappe.qb.from_(delivery_note_item)
			.select(
				delivery_note_item.against_sales_invoice.as_("parent"),
				GroupConcatWithSeparator(delivery_note_item.parent, ", ").as_("dn"),
			)
			.where(
				(delivery_note_item.docstatus == 1)
				& delivery_note_item.against_sales_invoice.isnotnull()
				& (delivery_note_item.against_sales_invoice != "")
				& delivery_note_item.against_sales_invoice.isin(voucher_nos)
			)
			.groupby(delivery_note_item.against_sales_invoice)
		).run(as_dict=True):
			if si.parent in dn_details:
				dn_details[si.parent] += ', %s' %(si.dn)
			else:
				dn_details.setdefault(si.parent, si.dn)

	return dn_details

def get_voucher_details(party_type, voucher_nos, dn_details):
	voucher_details = frappe._dict()

	if party_type == "Customer":
		sales_invoice = frappe.qb.DocType("Sales Invoice")
		sales_team = frappe.qb.DocType("Sales Team")
		for si in (
			frappe.qb.from_(sales_invoice)
			.left_join(sales_team)
			.on((sales_team.parent == sales_invoice.name) & (sales_team.parenttype == "Sales Invoice"))
			.select(
				sales_invoice.name,
				sales_invoice.due_date,
				sales_invoice.po_no,
				GroupConcatWithSeparator(sales_team.sales_person, ", ").as_("sales_person"),
			)
			.where((sales_invoice.docstatus == 1) & sales_invoice.name.isin(voucher_nos))
			.groupby(sales_invoice.name)
		).run(as_dict=True):
				si['delivery_note'] = dn_details.get(si.name)
				voucher_details.setdefault(si.name, si)

	if party_type == "Supplier":
		purchase_invoice = frappe.qb.DocType("Purchase Invoice")
		for pi in (
			frappe.qb.from_(purchase_invoice)
			.select(purchase_invoice.name, purchase_invoice.due_date, purchase_invoice.bill_no, purchase_invoice.bill_date)
			.where((purchase_invoice.docstatus == 1) & purchase_invoice.name.isin(voucher_nos))
		).run(as_dict=True):
			voucher_details.setdefault(pi.name, pi)

	journal_entry = frappe.qb.DocType("Journal Entry")
	for pi in (
		frappe.qb.from_(journal_entry)
		.select(journal_entry.name, journal_entry.due_date, journal_entry.bill_no, journal_entry.bill_date)
		.where(
			(journal_entry.docstatus == 1)
			& journal_entry.bill_no.isnotnull()
			& journal_entry.name.isin(voucher_nos)
		)
	).run(as_dict=True):
			voucher_details.setdefault(pi.name, pi)

	return voucher_details
