# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	columns = [
		{"fieldname": "type", "label": _("Type"), "fieldtype": "Data", "options": "", "width": 150},
		{"fieldname": "line", "label": _("Line"), "fieldtype": "Data", "options": "", "width": 100},
		{"fieldname": "excl", "label": _("Excl Amount"), "fieldtype": "Float", "options": "", "width": 150},
		{"fieldname": "vat", "label": _("VAT Amount"), "fieldtype": "Float", "options": "", "width": 150},
		{"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "options": "", "width": 300},
	]
	return columns


def get_data(filters):
	imported = {
		"type": "Foreign Purchase",
		"line": "Line 3",
		"excl": 0,
		"vat": 0,
		"category": "Value of imported services",
	}
	non_creditable_purchases = {
		"type": "Purchase",
		"line": "Line 2",
		"excl": 0,
		"vat": 0,
		"category": "Non-creditable purchases",
	}
	taxable_purchases = {
		"type": "Purchase",
		"line": "Line 1",
		"excl": 0,
		"vat": 0,
		"category": "Taxable purchases",
	}

	purchase_list = frappe.get_all(
		"Purchase Invoice",
		filters={
			"docstatus": 1,
			"is_return": 0,
			"company": filters.company,
			"posting_date": ["between", [filters.from_date, filters.to_date]],
		},
		fields={"*"},
	)

	for element in purchase_list:
		country = frappe.get_value("Supplier", element.supplier, "country")
		if country and country != "Tanzania":
			imported["excl"] += element.base_net_total
		elif not element.base_total_taxes_and_charges:
			non_creditable_purchases["excl"] += element.base_net_total
		else:
			taxable_purchases["vat"] += element.base_total_taxes_and_charges
			taxable = element.base_total_taxes_and_charges / 0.18
			taxable_purchases["excl"] += taxable
			non_creditable = element.base_net_total - taxable
			non_creditable_purchases["excl"] += non_creditable

	non_creditable_supplies = {
		"type": "Sales",
		"line": "Line 2",
		"excl": 0,
		"vat": 0,
		"category": "Non-creditable supplies",
	}
	taxable_supplies = {
		"type": "Sales",
		"line": "Line 1",
		"excl": 0,
		"vat": 0,
		"category": "Taxable supplies",
	}

	sales_list = frappe.get_all(
		"Sales Invoice",
		filters={
			"docstatus": 1,
			"is_return": 0,
			"status": ["!=", "Credit Note Issued"],
			"company": filters.company,
			"posting_date": ["between", [filters.from_date, filters.to_date]],
		},
		fields={"*"},
	)

	for element in sales_list:
		if not element.base_total_taxes_and_charges:
			non_creditable_supplies["excl"] += element.base_net_total
		else:
			taxable_supplies["vat"] += element.base_total_taxes_and_charges
			taxable = element.base_total_taxes_and_charges / 0.18
			taxable_supplies["excl"] += taxable
			non_creditable = element.base_net_total - taxable
			non_creditable_supplies["excl"] += non_creditable

	return [taxable_purchases, non_creditable_purchases, taxable_supplies, non_creditable_supplies, imported]
