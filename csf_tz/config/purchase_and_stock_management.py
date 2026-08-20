from frappe import _


def get_data():
	return [
		{
			"label": _("Purchasing"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Material Request",
					"description": _("Request for purchase."),
				},
				{
					"type": "doctype",
					"name": "Request for Quotation",
					"description": _("Request for quotation."),
				},
				{
					"type": "doctype",
					"name": "Supplier Quotation",
					"description": _("Quotations received from Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Purchase Order",
					"description": _("Purchase Orders given to Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Order Tracking",
					"description": _("Track orders from Suppliers."),
				},
				{"type": "doctype", "name": "Product Quality Inspection", "label": _("Order Inspection")},
				{
					"type": "doctype",
					"name": "Purchase Receipt",
				},
			],
		},
		{
			"label": _("Stock Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Stock Entry",
				},
				{
					"type": "doctype",
					"name": "Stock Transport",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Ledger",
					"doctype": "Stock Ledger Entry",
				},
			],
		},
		{
			"label": _("Supplier"),
			"items": [
				{
					"type": "doctype",
					"name": "Supplier",
					"description": _("Supplier database."),
				},
				{"type": "doctype", "name": "Supplier Type", "description": _("Supplier Type master.")},
				{
					"type": "doctype",
					"name": "Project",
					"label": _("Projects"),
					"description": _("Supplier Type master."),
				},
			],
		},
		{
			"label": _("Items and Pricing"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
				},
				{
					"type": "doctype",
					"name": "Product Bundle",
				},
				{
					"type": "doctype",
					"name": "Item Price",
					"route": "Report/Item Price",
				},
				{
					"type": "doctype",
					"name": "Serial No",
				},
				{
					"type": "doctype",
					"name": "Past Serial No",
					"description": _("Past Serial No."),
				},
			],
		},
		{
			"label": _("Purchase Reports"),
			"icon": "fa fa-list",
			"items": [
				{"type": "report", "is_query_report": True, "name": "Items To Be Requested"},
				{"type": "report", "is_query_report": True, "name": "Reordering Items"},
				{"type": "report", "is_query_report": True, "name": "Pending Ordered Items"},
				{"type": "report", "is_query_report": True, "name": "Purchase History"},
				{"type": "report", "is_query_report": True, "name": "Pending Requests"},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Shipment Tracking",
					"doctype": "Order Tracking",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Costing Report",
					"doctype": "Landed Cost Voucher",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Supplier Contacts",
					"label": "Supplier Contacts",
					"doctype": "Address",
					"route_options": {"party_type": "Supplier"},
				},
			],
		},
		{
			"label": _("Stock Reports"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Balance",
					"doctype": "Stock Ledger Entry",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Projected Qty",
					"doctype": "Item",
				},
				{"type": "page", "name": "stock-balance", "label": _("Stock Summary")},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Stock Ageing",
					"doctype": "Item",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Ordered Items To Be Delivered",
					"doctype": "Delivery Note",
				},
				{
					"type": "report",
					"name": "Item Shortage Report",
					"route": "Report/Bin/Item Shortage Report",
					"doctype": "Purchase Receipt",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Requested Items To Be Transferred",
					"doctype": "Material Request",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Itemwise Recommended Reorder Level",
					"doctype": "Item",
				},
			],
		},
		{
			"label": _("Purchase Analytics"),
			"icon": "fa fa-table",
			"items": [
				{
					"type": "page",
					"name": "purchase-analytics",
					"label": _("Purchase Analytics"),
					"icon": "fa fa-bar-chart",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Order Trends",
					"doctype": "Purchase Order",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Purchase Receipt Trends",
					"doctype": "Purchase Receipt",
				},
			],
		},
		{
			"label": _("Stock Analytics"),
			"icon": "fa fa-table",
			"items": [
				{
					"type": "page",
					"name": "stock-analytics",
					"label": _("Stock Analytics"),
					"icon": "fa fa-bar-chart",
				},
				{"type": "doctype", "name": "Bin Setup", "description": _("Bin Setup for warehouse")},
			],
		},
	]
