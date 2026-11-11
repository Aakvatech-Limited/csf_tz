import frappe
from frappe.desk.reportview import build_match_conditions
from frappe.query_builder import Order
from frappe.query_builder.custom import GROUP_CONCAT
from frappe.query_builder.functions import Sum
from pypika.terms import Bracket, LiteralValue


class GroupConcatWithSeparator(GROUP_CONCAT):
	"""GROUP_CONCAT with a SEPARATOR clause and an optional ORDER BY."""

	def __init__(self, column, separator, order_by=None, alias=None):
		super().__init__(column, alias=alias)
		self.separator = separator
		self.order_by = order_by

	def get_special_params_sql(self, **kwargs):
		order_by = f"ORDER BY {self.order_by.get_sql(**kwargs)} " if self.order_by is not None else ""
		return f"{order_by}SEPARATOR '{self.separator}'"


def get_match_criterion(doctype):
	"""User permission conditions of `doctype` as a criterion, or None for an unrestricted user.

	Frappe v15 query builder has no permission-aware path, so the SQL from build_match_conditions is wrapped as is.
	"""
	match_conditions = build_match_conditions(doctype)
	return Bracket(LiteralValue(match_conditions)) if match_conditions else None


def get_latest_reporting_status_query(parent, parenttype, parentfield=None):
	"""Subquery for the status of the newest Reporting Status Table row of `parent`."""
	reporting_status = frappe.qb.DocType("Reporting Status Table")
	query = (
		frappe.qb.from_(reporting_status)
		.select(reporting_status.status)
		.where(reporting_status.parenttype == parenttype)
		.where(reporting_status.parent == parent)
	)
	if parentfield:
		query = query.where(reporting_status.parentfield == parentfield)
	return query.orderby(reporting_status.datetime, order=Order.desc).limit(1)


def get_expenses_total_query(parent, parenttype, currency):
	"""Subquery for the total Expenses of `parent` in `currency`."""
	expenses = frappe.qb.DocType("Expenses")
	return (
		frappe.qb.from_(expenses)
		.select(Sum(expenses.expense_amount))
		.where(expenses.parenttype == parenttype)
		.where(expenses.parent == parent)
		.where(expenses.expense_currency == currency)
	)
