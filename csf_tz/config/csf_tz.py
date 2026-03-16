from __future__ import unicode_literals
from frappe import _


def get_data():
	return [
		{
			"label": _("Tax Compliance"),
			"items": [
				{
					"type": "doctype",
					"name": "EFD Z Report",
					"description": _("Accounting journal entries with Multi-Currency."),
				},
				{
					"type": "doctype",
					"name": "Electronic Fiscal Device",
					"description": _("Electronic Fiscal Device setup."),
				},
			],
		},
		{
			"label": _("Corporate Compliance"),
			"items": [
				{
					"type": "doctype",
					"name": "Open Invoice Exchange Rate Revaluation",
					"description": _("Open Invoice Exchange Rate Revaluation for period end P & L visibility."),
				},
			],
		},
		{
			"label": _("Petty Expense"),
			"items": [
				{
					"type": "doctype",
					"name": "Expense Record",
					"description": _("Petty expenses for Section. Intelligent expense transactions."),
				},
				{
					"type": "doctype",
					"name": "Expense Type",
					"description": _("Expense type to make petty expenses and linking to expense accounts."),
				},
			],
		},
		{
			"label": _("Tax Analytics"),
			"items": [
				{
					"type": "report",
					"name": "TRA Input VAT Returns eFiling",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Withholding Tax Summary on Sales",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Withholding Tax Summary on Sales",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Withholding Tax Payment Summary",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "ITX 230.01.E – Withholding Tax Statement",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Output VAT Reconciliation",
					"doctype": "EFD Z Report",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Credit Note List",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Purchase Reports by Tax Category",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Purchases by Tax Category Summary",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
			],
		},
		{
			"label": _("HR Analytics"),
			"items": [
				{
					"type": "report",
					"name": "Employment History",
					"doctype": "Employee",
					"is_query_report": True
				},
			],
		},
		{
			"label": _("Business Analytics"),
			"items": [
				{
					"type": "report",
					"name": "Multi-Currency Ledger",
					"doctype": "GL Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Trial Balance Report in USD",
					"doctype": "GL Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Itemwise Stock Movement",
					"doctype": "Stock Ledger Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Warehouse wise Item Balance and Value",
					"doctype": "Stock Ledger Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Receivable Multi Currency",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Stock Balance pivot warehouse",
					"doctype": "Stock Ledger Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Receivable Summary Multi Currency",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
			]
		},
		{
			"label": _("Other features"),
			"items": [
				{
					"type": "doctype",
					"name": "Repack Template",
					"description": _("Quick BOM feature for repacking. Making many items of one item"),
				},
			],
		},
		{
			"label": _("Settings"),
			"items": [
				{
					"type": "doctype",
					"name": "CSF TZ Settings",
					"description": _("Settings for CSF TZ."),
				},
			],
		},
	]
