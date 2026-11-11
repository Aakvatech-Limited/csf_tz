# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from erpnext import get_company_currency, get_default_company
from erpnext.accounts.report.utils import get_currency, convert_to_presentation_currency
from frappe.utils import getdate, cstr, flt, fmt_money
from frappe import _, _dict
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from six import iteritems
from collections import OrderedDict
from frappe.query_builder import Criterion
from csf_tz.csf_tz.report.gl_entry_conditions import (
	get_child_accounts_query,
	get_dimension_conditions,
	get_finance_book_condition,
	get_party_conditions,
	get_posting_date_conditions,
)
from csf_tz.utils.query_builder import get_match_criterion

def execute(filters=None):
	if not filters:
		return [], []

	account_details = {}

	if filters and filters.get('print_in_account_currency') and \
		not filters.get('account'):
		frappe.throw(_("Select an account to print in account currency"))

	account = frappe.qb.DocType("Account")
	for acc in frappe.qb.from_(account).select(account.name, account.is_group).run(as_dict=True):
		account_details.setdefault(acc.name, acc)

	if filters.get('party'):
		filters.party = frappe.parse_json(filters.get("party"))

	validate_filters(filters, account_details)

	validate_party(filters)

	filters = set_account_currency(filters)

	columns = get_columns(filters)

	res = get_result(filters, account_details)

	return columns, res


def validate_filters(filters, account_details):
	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))

	if not filters.get("from_date") and not filters.get("to_date"):
		frappe.throw(_("{0} and {1} are mandatory").format(frappe.bold(_("From Date")), frappe.bold(_("To Date"))))

	if filters.get("account") and not account_details.get(filters.account):
		frappe.throw(_("Account {0} does not exists").format(filters.account))

	if (filters.get("account") and filters.get("group_by") == _('Group by Account')
		and account_details[filters.account].is_group == 0):
		frappe.throw(_("Can not filter based on Account, if grouped by Account"))

	if (filters.get("voucher_no")
		and filters.get("group_by") in [_('Group by Voucher')]):
		frappe.throw(_("Can not filter based on Voucher No, if grouped by Voucher"))

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	if filters.get('project'):
		filters.project = frappe.parse_json(filters.get('project'))

	if filters.get('cost_center'):
		filters.cost_center = frappe.parse_json(filters.get('cost_center'))


def validate_party(filters):
	party_type, party = filters.get("party_type"), filters.get("party")

	if party:
		if not party_type:
			frappe.throw(_("To filter based on Party, select Party Type first"))
		else:
			for d in party:
				if not frappe.db.exists(party_type, d):
					frappe.throw(_("Invalid {0}: {1}").format(party_type, d))

def set_account_currency(filters):
	if filters.get("account") or (filters.get('party') and len(filters.party) == 1):
		filters["company_currency"] = frappe.get_cached_value('Company',  filters.company,  "default_currency")
		account_currency = None

		if filters.get("account"):
			account_currency = get_account_currency(filters.account)
		elif filters.get("party"):
			gle_currency = frappe.db.get_value(
				"GL Entry", {
					"party_type": filters.party_type, "party": filters.party[0], "company": filters.company
				},
				"account_currency"
			)

			if gle_currency:
				account_currency = gle_currency
			else:
				account_currency = (None if filters.party_type in ["Employee", "Student", "Shareholder", "Member"] else
					frappe.db.get_value(filters.party_type, filters.party[0], "default_currency"))

		filters["account_currency"] = account_currency or filters.company_currency
		if filters.account_currency != filters.company_currency and not filters.presentation_currency:
			filters.presentation_currency = filters.account_currency

	return filters

def get_result(filters, account_details):
	gl_entries = get_gl_entries(filters)

	data = get_data_with_opening_closing(filters, account_details, gl_entries)

	result = get_result_as_list(data, filters)

	return result

def get_gl_entries(filters):
	currency_map = get_currency(filters)
	gl_entry = frappe.qb.DocType("GL Entry")

	if filters.get("include_default_book_entries"):
		filters['company_fb'] = frappe.db.get_value("Company",
			filters.get("company"), 'default_finance_book')

	query = (
		frappe.qb.from_(gl_entry)
		.select(
			gl_entry.name.as_("gl_entry"), gl_entry.posting_date, gl_entry.account, gl_entry.party_type, gl_entry.party,
			gl_entry.voucher_type, gl_entry.voucher_no, gl_entry.cost_center, gl_entry.project,
			gl_entry.against_voucher_type, gl_entry.against_voucher, gl_entry.account_currency,
			gl_entry.remarks, gl_entry.against, gl_entry.is_opening, gl_entry.debit, gl_entry.credit,
			gl_entry.debit_in_account_currency, gl_entry.credit_in_account_currency,
		)
		.where(gl_entry.company == filters.company)
		.where(Criterion.all(get_conditions(filters, gl_entry)))
	)

	if filters.get("group_by") == _("Group by Voucher"):
		query = query.orderby(gl_entry.posting_date, gl_entry.voucher_type, gl_entry.voucher_no)
	else:
		query = query.orderby(gl_entry.posting_date, gl_entry.account, gl_entry.creation)

	gl_entries = query.run(as_dict=True)

	if filters.get('presentation_currency'):
		return convert_to_presentation_currency(gl_entries, currency_map)
	else:
		return gl_entries


def get_conditions(filters, gl_entry):
	conditions = []
	if filters.get("account"):
		conditions.append(gl_entry.account.isin(get_child_accounts_query(filters["account"])))

	if filters.get("cost_center"):
		filters.cost_center = get_cost_centers_with_children(filters.cost_center)
		conditions.append(gl_entry.cost_center.isin(filters.cost_center))

	if filters.get("voucher_no"):
		conditions.append(gl_entry.voucher_no == filters.voucher_no)

	conditions += get_party_conditions(filters, gl_entry)
	conditions += get_posting_date_conditions(filters, gl_entry)

	if filters.get("project"):
		conditions.append(gl_entry.project.isin(filters.project))

	if filters.get("finance_book"):
		conditions.append(get_finance_book_condition(filters, gl_entry))

	match_criterion = get_match_criterion("GL Entry")
	if match_criterion:
		conditions.append(match_criterion)

	conditions += get_dimension_conditions(filters, gl_entry)

	return conditions


def get_data_with_opening_closing(filters, account_details, gl_entries):
	data = []

	gle_map = initialize_gle_map(gl_entries, filters)

	totals, entries = get_accountwise_gle(filters, gl_entries, gle_map)

	# Opening for filtered account
	data.append(totals.opening)

	if filters.get("group_by") != _('Group by Voucher (Consolidated)'):
		for acc, acc_dict in iteritems(gle_map):
			# acc
			if acc_dict.entries:
				# opening
				data.append({})
				if filters.get("group_by") != _("Group by Voucher"):
					data.append(acc_dict.totals.opening)

				data += acc_dict.entries

				# totals
				data.append(acc_dict.totals.total)

				# closing
				if filters.get("group_by") != _("Group by Voucher"):
					data.append(acc_dict.totals.closing)
		data.append({})
	else:
		data += entries

	# totals
	data.append(totals.total)

	# closing
	data.append(totals.closing)

	return data

def get_totals_dict():
	def _get_debit_credit_dict(label):
		return _dict(
			account="'{0}'".format(label),
			debit=0.0,
			credit=0.0,
			debit_in_account_currency=0.0,
			credit_in_account_currency=0.0
		)
	return _dict(
		opening = _get_debit_credit_dict(_('Opening')),
		total = _get_debit_credit_dict(_('Total')),
		closing = _get_debit_credit_dict(_('Closing (Opening + Total)'))
	)

def group_by_field(group_by):
	if group_by == _('Group by Party'):
		return 'party'
	elif group_by in [_('Group by Voucher (Consolidated)'), _('Group by Account')]:
		return 'account'
	else:
		return 'voucher_no'

def initialize_gle_map(gl_entries, filters):
	gle_map = OrderedDict()
	group_by = group_by_field(filters.get('group_by'))

	for gle in gl_entries:
		gle_map.setdefault(gle.get(group_by), _dict(totals=get_totals_dict(), entries=[]))
	return gle_map


def get_accountwise_gle(filters, gl_entries, gle_map):
	totals = get_totals_dict()
	entries = []
	consolidated_gle = OrderedDict()
	group_by = group_by_field(filters.get('group_by'))

	def update_value_in_dict(data, key, gle):
		data[key].debit += flt(gle.debit)
		data[key].credit += flt(gle.credit)

		data[key].debit_in_account_currency += flt(gle.debit_in_account_currency)
		data[key].credit_in_account_currency += flt(gle.credit_in_account_currency)

		if data[key].against_voucher and gle.against_voucher:
			data[key].against_voucher += ', ' + gle.against_voucher

	from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)
	for gle in gl_entries:
		if (gle.posting_date < from_date or
			(cstr(gle.is_opening) == "Yes" and not filters.get("show_opening_entries"))):
			update_value_in_dict(gle_map[gle.get(group_by)].totals, 'opening', gle)
			update_value_in_dict(totals, 'opening', gle)

			update_value_in_dict(gle_map[gle.get(group_by)].totals, 'closing', gle)
			update_value_in_dict(totals, 'closing', gle)

		elif gle.posting_date <= to_date:
			update_value_in_dict(gle_map[gle.get(group_by)].totals, 'total', gle)
			update_value_in_dict(totals, 'total', gle)
			if filters.get("group_by") != _('Group by Voucher (Consolidated)'):
				gle_map[gle.get(group_by)].entries.append(gle)
			elif filters.get("group_by") == _('Group by Voucher (Consolidated)'):
				key = (gle.get("voucher_type"), gle.get("voucher_no"),
					gle.get("account"), gle.get("cost_center"))
				if key not in consolidated_gle:
					consolidated_gle.setdefault(key, gle)
				else:
					update_value_in_dict(consolidated_gle, key, gle)

			update_value_in_dict(gle_map[gle.get(group_by)].totals, 'closing', gle)
			update_value_in_dict(totals, 'closing', gle)

	for key, value in consolidated_gle.items():
		entries.append(value)

	return totals, entries

def get_result_as_list(data, filters):
	balance, balance_in_account_currency = 0, 0
	inv_details = get_supplier_invoice_details()

	for d in data:
		if not d.get('posting_date'):
			balance, balance_in_account_currency = 0, 0

		balance = get_balance(d, balance, 'debit', 'credit')
		d['balance'] = balance

		d['account_currency'] = filters.account_currency
		d['bill_no'] = inv_details.get(d.get('against_voucher'), '')

	return data

def get_supplier_invoice_details():
	inv_details = {}
	purchase_invoice = frappe.qb.DocType("Purchase Invoice")
	supplier_invoices = (
		frappe.qb.from_(purchase_invoice)
		.select(purchase_invoice.name, purchase_invoice.bill_no)
		.where(purchase_invoice.docstatus == 1)
		.where(purchase_invoice.bill_no.isnotnull())
		.where(purchase_invoice.bill_no != "")
		.run(as_dict=True)
	)
	for d in supplier_invoices:
		inv_details[d.name] = d.bill_no

	return inv_details

def get_balance(row, balance, debit_field, credit_field):
	balance += (row.get(debit_field, 0) -  row.get(credit_field, 0))

	return balance

def get_columns(filters):
	if filters.get("presentation_currency"):
		currency = filters["presentation_currency"]
	else:
		if filters.get("company"):
			currency = get_company_currency(filters["company"])
		else:
			company = get_default_company()
			currency = get_company_currency(company)

	columns = [
		{
			"label": _("GL Entry"),
			"fieldname": "gl_entry",
			"fieldtype": "Link",
			"options": "GL Entry",
			"hidden": 1
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 90
		},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 180
		},
		{
			"label": _("Debit ({0})".format(currency)),
			"fieldname": "debit",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Credit ({0})".format(currency)),
			"fieldname": "credit",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Balance ({0})".format(currency)),
			"fieldname": "balance",
			"fieldtype": "Float",
			"width": 130
		}
	]

	columns.extend([
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"width": 120
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 180
		},
		{
			"label": _("Against Account"),
			"fieldname": "against",
			"width": 120
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"width": 100
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"width": 100
		},
		{
			"label": _("Project"),
			"options": "Project",
			"fieldname": "project",
			"width": 100
		},
		{
			"label": _("Cost Center"),
			"options": "Cost Center",
			"fieldname": "cost_center",
			"width": 100
		},
		{
			"label": _("Against Voucher Type"),
			"fieldname": "against_voucher_type",
			"width": 100
		},
		{
			"label": _("Against Voucher"),
			"fieldname": "against_voucher",
			"fieldtype": "Dynamic Link",
			"options": "against_voucher_type",
			"width": 100
		},
		{
			"label": _("Supplier Invoice No"),
			"fieldname": "bill_no",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Remarks"),
			"fieldname": "remarks",
			"width": 400
		}
	])

	return columns
