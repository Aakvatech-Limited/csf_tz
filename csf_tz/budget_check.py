# -*- coding: utf-8 -*-
# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

"""
Budget Check Utility Functions

This module provides functionality to check budget for documents in draft status
before submission, particularly useful for approval workflows.

This module hooks into the server-side validate event to perform blocking
budget validation when documents are saved in draft status.
"""

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.budget.budget import validate_expense_against_budget


def validate_budget_on_draft(doc, method=None):
	"""
	Server-side validate hook to check budget for documents in draft status.

	This function is called automatically via doc_events hooks in hooks.py
	when a document is being validated (saved). It checks if the feature flag
	is enabled for the doctype and performs budget validation if so.

	Args:
		doc: The document being validated
		method: The event method name (not used, required by Frappe hooks)

	Note:
		This function relies on ERPNext's native budget validation.
		Any budget violations will be raised as exceptions that block
		the save operation and display error messages to the user.
	"""
	# Only check if document is in draft status
	if doc.docstatus != 0:
		return

	# Check if there are any budgets configured
	if not frappe.get_all("Budget", limit=1):
		return

	# Check if feature flag is enabled for this doctype
	if not is_budget_check_enabled(doc.doctype):
		return

	# Perform budget check based on doctype
	# Let ERPNext's validate_expense_against_budget raise exceptions naturally
	# These exceptions will block the save operation
	if doc.doctype == "Journal Entry":
		check_budget_for_journal_entry(doc)
	elif doc.doctype in ["Material Request", "Purchase Order", "Purchase Invoice"]:
		check_budget_for_buying_document(doc)


def is_budget_check_enabled(doctype):
	"""
	Check if budget check feature is enabled for the given doctype.

	Args:
		doctype (str): The doctype to check

	Returns:
		bool: True if feature is enabled, False otherwise
	"""
	# Map doctype to setting field name
	setting_field_map = {
		"Journal Entry": "enable_budget_check_button_for_journal_entry",
		"Material Request": "enable_budget_check_button_for_material_request",
		"Purchase Order": "enable_budget_check_button_for_purchase_order",
		"Purchase Invoice": "enable_budget_check_button_for_purchase_invoice",
	}

	setting_field = setting_field_map.get(doctype)
	if not setting_field:
		return False

	try:
		return frappe.db.get_single_value("CSF TZ Settings", setting_field) or False
	except Exception:
		return False


@frappe.whitelist()
def check_budget_before_submit(doctype, docname, setting_field=None):
	"""
	Check budget for a document in draft status.

	This function validates budget against the document's items/accounts
	without actually submitting the document. It's designed to be called
	automatically on validate event to give users early warning about budget issues.

	Args:
		doctype (str): The doctype to check (Journal Entry, Material Request, Purchase Order, Purchase Invoice)
		docname (str): The name of the document to check
		setting_field (str, optional): The CSF TZ Settings field name to check if budget check is enabled.
			If not provided, the function will automatically determine the field based on doctype.

	Note:
		This function relies on ERPNext's native budget validation.
		Any budget violations will be raised as exceptions that ERPNext's
		framework will display to the user automatically.
	"""
	# Validate inputs
	if not doctype or not docname:
		return

	# Mapping of doctypes to their corresponding CSF TZ Settings fields
	doctype_to_setting_field = {
		"Journal Entry": "enable_budget_check_button_for_journal_entry",
		"Material Request": "enable_budget_check_button_for_material_request",
		"Purchase Order": "enable_budget_check_button_for_purchase_order",
		"Purchase Invoice": "enable_budget_check_button_for_purchase_invoice"
	}

	# Check if doctype is supported
	if doctype not in doctype_to_setting_field:
		return

	# Determine which setting field to check
	# Prioritize the automatically mapped field, but allow override via setting_field parameter
	field_to_check = setting_field if setting_field else doctype_to_setting_field.get(doctype)

	# Check if budget check feature is enabled for this doctype
	if field_to_check:
		try:
			is_enabled = frappe.db.get_single_value('CSF TZ Settings', field_to_check)
			if not is_enabled:
				return
		except Exception:
			# If setting field doesn't exist or error occurs, skip budget check
			return

	# Get the document
	try:
		doc = frappe.get_doc(doctype, docname)
	except Exception:
		return

	# Check if document is in draft status
	if doc.docstatus != 0:
		return

	# Check if there are any budgets configured
	if not frappe.get_all("Budget", limit=1):
		return

	# Perform budget check based on doctype
	# Let ERPNext's validate_expense_against_budget raise exceptions naturally
	if doctype == "Journal Entry":
		check_budget_for_journal_entry(doc)
	elif doctype in ["Material Request", "Purchase Order", "Purchase Invoice"]:
		check_budget_for_buying_document(doc)


def check_budget_for_journal_entry(doc):
	"""
	Check budget for Journal Entry document.

	For Journal Entry, budget is checked against each account entry
	when making GL entries.

	Note:
		This function calls ERPNext's validate_expense_against_budget
		which will raise exceptions for budget violations. These exceptions
		will be caught by Frappe's framework and displayed to the user.
	"""
	for account in doc.get("accounts"):
		if account.account and account.cost_center:
			# Prepare args for budget validation
			args = {
				"account": account.account,
				"cost_center": account.cost_center,
				"company": doc.company,
				"posting_date": doc.posting_date,
				"doctype": doc.doctype,
			}

			# Add other accounting dimensions if present
			if hasattr(account, 'project') and account.project:
				args["project"] = account.project

			# Calculate expense amount (debit - credit)
			expense_amount = flt(account.debit) - flt(account.credit)

			# Let ERPNext's validation raise exceptions naturally
			validate_expense_against_budget(args, expense_amount=expense_amount)


def check_budget_for_buying_document(doc):
	"""
	Check budget for Material Request, Purchase Order, or Purchase Invoice.

	These documents have items and the budget is checked against each item.

	Note:
		This function calls ERPNext's validate_expense_against_budget
		which will raise exceptions for budget violations. These exceptions
		will be caught by Frappe's framework and displayed to the user.
	"""
	for item in doc.get("items"):
		# Prepare args for budget validation
		args = item.as_dict()

		# Determine the correct date field based on doctype
		# Material Request: uses schedule_date (or transaction_date as fallback)
		# Purchase Order: uses transaction_date
		# Purchase Invoice: uses posting_date
		if doc.doctype == "Material Request":
			posting_date = doc.schedule_date or doc.transaction_date
		elif doc.doctype == "Purchase Order":
			posting_date = doc.transaction_date
		elif doc.doctype == "Purchase Invoice":
			posting_date = doc.posting_date
		else:
			posting_date = doc.get("posting_date") or doc.get("transaction_date")

		args.update({
			"doctype": doc.doctype,
			"company": doc.company,
			"posting_date": posting_date,
		})

		# Ensure project field is included if present
		# This is critical for project-based budget validation
		if hasattr(item, 'project') and item.project:
			args["project"] = item.project

		# Calculate the item amount for budget validation
		# This is critical - we must pass the current document's amount
		# because ERPNext's get_ordered_amount only counts submitted POs
		item_amount = flt(item.get("amount")) or (flt(item.get("qty")) * flt(item.get("rate")))

		# Let ERPNext's validation raise exceptions naturally
		# Pass expense_amount so it includes the current draft document's amount
		validate_expense_against_budget(args, expense_amount=item_amount)

