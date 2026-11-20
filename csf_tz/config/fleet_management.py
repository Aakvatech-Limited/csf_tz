from frappe import _


def get_data():
	return [
		{
			"label": _("Documents"),
			"items": [
				{"type": "doctype", "name": "Files", "description": _("Files.")},
				{"type": "doctype", "name": "Fuel Request", "description": _("Fuel Request.")},
				{"type": "doctype", "name": "Transport Request", "description": _("Transport Request.")},
				{
					"type": "doctype",
					"name": "Transport Assignment",
					"description": _("Transport Assignment."),
				},
				{"type": "doctype", "name": "Vehicle Trip", "description": _("Vehicle trips.")},
				{"type": "doctype", "name": "Vehicle Inspection", "description": _("Vehicle Inspection.")},
			],
		},
		{
			"label": _("Setup"),
			"items": [
				{"type": "doctype", "name": "Vehicle", "description": _("Registered Vehicles")},
				{"type": "doctype", "name": "Trailer", "description": _("Registered Trailers")},
				{"type": "doctype", "name": "Trip Route", "description": _("Trip Route")},
				{"type": "doctype", "name": "Trip Location Type", "description": _("Trip Location Type")},
				{"type": "doctype", "name": "Trip Location", "description": _("Trip Location")},
				{"type": "doctype", "name": "Fixed Expense", "description": _("Fixed Expense")},
				{"type": "doctype", "name": "Unit of Measure", "description": _("Unit of Measure")},
				{
					"type": "doctype",
					"name": "Vehicle Documents Type",
					"description": _("Vehicle Documents Type"),
				},
				{"type": "doctype", "name": "Vehicle Type", "description": _("Vehicle Type")},
				{
					"type": "doctype",
					"name": "Vehicle Inspection Template",
					"description": _("Vehicle Inspection Template"),
				},
			],
		},
		{
			"label": _("Internal Reports"),
			"items": [
				{
					"type": "report",
					"name": "Trip Report",
					"doctype": "Vehicle Trip",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Fuel Report",
					"doctype": "Vehicle Trip",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Vehicle Status Report",
					"doctype": "Vehicle Trip",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Truck Document Expiration Report",
					"doctype": "Vehicle",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Transport Assignment Report",
					"doctype": "Transport Assignment",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Vehicles En Route to Border",
					"doctype": "Vehicle Trip",
					"is_query_report": True,
				},
			],
		},
		{
			"label": _("Daily Customer Reports"),
			"items": [
				{
					"type": "report",
					"name": "Daily Customer Report - Transport",
					"doctype": "Vehicle Trip",
					"is_query_report": True,
				}
			],
		},
	]
