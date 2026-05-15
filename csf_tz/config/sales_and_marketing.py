from __future__ import unicode_literals

from frappe import _


def get_data():
	return [
		{
			"label": _("Marketing"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Lead",
					"description": _("Database of potential customers."),
				},
				{
					"type": "doctype",
					"name": "Customer",
					"description": _("Customer database."),
				},
				{
					"type": "doctype",
					"name": "Customer Loan Assistance",
					"description": _("Customer Loan Assistance."),
				},
			],
		},
		{
			"label": _("Sales"),
			"icon": "fa fa-star",
			"items": [
				{"type": "page", "name": "pos", "label": _("POS"), "description": _("Point of Sale")},
				{
					"type": "doctype",
					"name": "Quotation",
					"description": _("Quotes to Leads or Customers."),
				},
				{
					"type": "doctype",
					"name": "Sales Order",
					"description": _("Confirmed orders from Customers."),
				},
				{
					"type": "doctype",
					"name": "Sales Invoice",
					"description": _("Sales Invoices."),
				},
			],
		},
		{
			"label": _("Lead Follow Up"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"label": _("Due Follow Up Communications"),
					"name": "Due Communications",
					"doctype": "Lead",
				},
				{"type": "report", "is_query_report": True, "name": "Due Demonstrations", "doctype": "Lead"},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Loan Assistance Report",
					"doctype": "Customer Loan Assistance",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Item Wise Leads Report",
					"doctype": "Quotation",
				},
			],
		},
		{
			"label": _("Stock and Pricing"),
			"items": [
				{
					"type": "doctype",
					"name": "Item Price",
					"description": _("Multiple Item prices."),
					"route": "Report/Item Price",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Balance",
					"doctype": "Stock Ledger Entry",
				},
				{
					"type": "doctype",
					"name": "Past Serial No",
					"description": _("Past Serial No."),
				},
			],
		},
		{
			"label": _("Marketing Reports"),
			"icon": "fa fa-list",
			"items": [
				{
					"type": "doctype",
					"name": "Lead",
					"route": "List/Lead/Kanban/Sales Pipeline",
					"label": _("Sales Pipeline"),
				},
				{"type": "report", "is_query_report": True, "name": "Lead Details", "doctype": "Lead"},
				{
					"type": "page",
					"name": "sales-funnel",
					"label": _("Sales Funnel"),
					"icon": "fa fa-bar-chart",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Customer Addresses And Contacts",
					"doctype": "Contact",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Inactive Customers",
					"doctype": "Sales Order",
				},
				{"type": "report", "is_query_report": True, "name": "Campaign Efficiency", "doctype": "Lead"},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Lead Owner Efficiency",
					"doctype": "Lead",
				},
				{
					"type": "report",
					"is_query_report": True,
					"label": _("Follow Up Communications Report"),
					"name": "Communications",
					"doctype": "Lead",
				},
				{
					"type": "report",
					"is_query_report": True,
					"label": _("Demonstrations Report"),
					"name": "Demonstrations",
					"doctype": "Lead",
				},
			],
		},
		{
			"label": _("Sales Reports"),
			"icon": "fa fa-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Items Marked For Delivery",
					"doctype": "Sales Invoice",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Sales Person-wise Transaction Summary",
					"doctype": "Sales Order",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Item-wise Sales History",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Sales Order Trends",
					"doctype": "Sales Order",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Supplier-Wise Sales Analytics",
					"doctype": "Stock Ledger Entry",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Payment Plan Report",
					"doctype": "Sales Invoice",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Item Wise Sales Order",
					"doctype": "Sales Order",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Payment Plan Summary",
					"doctype": "Sales Invoice",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Sales Type Report",
					"doctype": "Sales Invoice",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Spare Sales Report",
					"doctype": "Sales Invoice",
				},
			],
		},
		{
			"label": _("Customer Reports"),
			"icon": "fa fa-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Brand Sales Report",
					"label": "Brandwise Customer Details",
					"doctype": "Sales Invoice",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Previous Ams Customer Report",
					"label": "Old Customers Details",
					"doctype": "Sales Invoice",
				},
			],
		},
		{
			"label": _("Setup"),
			"items": [
				{
					"type": "doctype",
					"label": _("Customer Group"),
					"name": "Customer Group",
					"icon": "fa fa-sitemap",
					"link": "Tree/Customer Group",
					"description": _("Manage Customer Group Tree."),
				},
				{
					"type": "doctype",
					"name": "Item Installation Procedures",
				},
				{
					"type": "doctype",
					"name": "Campaign",
					"description": _("Sales campaigns."),
				},
				{
					"type": "doctype",
					"name": "Loan Procedures",
					"label": "Supplier Loan Procedures",
					"description": _("Loan Procedures."),
				},
			],
		},
		{
			"label": _("Sales Analytics"),
			"icon": "fa fa-table",
			"items": [
				{
					"type": "page",
					"name": "sales-analytics",
					"label": _("Sales Analytics"),
					"icon": "fa fa-bar-chart",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Customer Acquisition and Loyalty",
					"doctype": "Customer",
					"icon": "fa fa-bar-chart",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Quotation Trends",
					"doctype": "Quotation",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Sales Order Trends",
					"doctype": "Sales Order",
				},
			],
		},
	]
