# -*- coding: utf-8 -*-
# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.budget.budget import validate_expense_against_budget


def check_budget_for_journal_entry(doc, method=None):
	"""
	Check budget for Journal Entry document.

	For Journal Entry, budget is checked against each account entry
	when making GL entries.
	"""
	if frappe.db.get_single_value(
		"CSF TZ Settings", "check_budget_in_je"
	):
		for account in doc.get("accounts") or []:
			# Check if account has at least one budget dimension (cost_center or project)
			# ERPNext's budget validation can work with either dimension independently
			has_cost_center = bool(getattr(account, "cost_center", None))
			has_project = bool(getattr(account, "project", None))

			if getattr(account, "account", None) and (has_cost_center or has_project):
				# Prepare args for budget validation
				args = {
					"account": account.account,
					"company": doc.company,
					"posting_date": doc.posting_date,
					"doctype": doc.doctype,
				}

				# Add cost_center if present (for cost center-based budgets)
				if has_cost_center:
					args["cost_center"] = account.cost_center

				# Add project if present (for project-based budgets)
				if has_project:
					args["project"] = account.project

				# Calculate expense amount (debit - credit)
				expense_amount = flt(getattr(account, "debit", 0)) - flt(getattr(account, "credit", 0))

				# Let ERPNext's validation raise exceptions naturally
				validate_expense_against_budget(args, expense_amount=expense_amount)


def check_budget_for_material_request(doc, method=None):
	"""
	Check budget for Material Request document.

	Material Request has items and the budget is checked against each item.
	"""
	if frappe.db.get_single_value(
		"CSF TZ Settings", "check_budget_in_mr"
	):
		for item in doc.get("items") or []:
			# Prepare args for budget validation
			args = item.as_dict()

			# Determine the correct date and expense field
			posting_date = doc.schedule_date or doc.transaction_date
			expense_amount = flt(getattr(item, "amount", 0))

			args.update(
				{
					"doctype": doc.doctype,
					"company": doc.company,
					"posting_date": posting_date,
				}
			)

			# Ensure project and cost_center field is included if present
			if getattr(item, "project", None):
				args["project"] = item.project
			if getattr(item, "cost_center", None):
				args["cost_center"] = item.cost_center

			# Pass expense_amount explicitly
			validate_expense_against_budget(args, expense_amount=expense_amount)


def check_budget_for_purchase_order(doc, method=None):
	"""
	Check budget for Purchase Order document.

	Purchase Order has items and the budget is checked against each item.
	"""
	if frappe.db.get_single_value(
		"CSF TZ Settings", "check_budget_in_po"
	):
		for item in doc.get("items") or []:
			# Prepare args for budget validation
			args = item.as_dict()

			# Determine the correct date and expense field
			posting_date = doc.transaction_date
			expense_amount = flt(getattr(item, "base_net_amount", 0))

			args.update(
				{
					"doctype": doc.doctype,
					"company": doc.company,
					"posting_date": posting_date,
				}
			)

			# Ensure project and cost_center field is included if present
			if getattr(item, "project", None):
				args["project"] = item.project
			if getattr(item, "cost_center", None):
				args["cost_center"] = item.cost_center

			# Pass expense_amount explicitly
			validate_expense_against_budget(args, expense_amount=expense_amount)

def check_budget_for_purchase_invoice(doc, method=None):
	"""
	Check budget for Purchase Invoice document.

	Purchase Invoice has items and the budget is checked against each item.
	"""
	if frappe.db.get_single_value("CSF TZ Settings", "check_budget_in_pi"):
		# frappe.throw("Budget check is enabled for Purchase Invoice")
		for item in doc.get("items") or []:
			# Prepare args for budget validation
			args = item.as_dict()

			# Determine the correct date and expense field
			posting_date = doc.posting_date
			expense_amount = flt(item.base_net_amount)

			args.update(
				{
					"doctype": doc.doctype,
					"company": doc.company,
					"posting_date": posting_date,
				}
			)

			# Ensure project and cost_center field is included if present
			if getattr(item, "project", None):
				args["project"] = item.project
			if getattr(item, "cost_center", None):
				args["cost_center"] = item.cost_center
			# frappe.throw(f"args: {args} and expense_amount: {expense_amount}")

			# Pass expense_amount explicitly
			validate_expense_against_budget(args, expense_amount=expense_amount)
