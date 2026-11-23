from frappe import _


def get_data():
	return [
		{
			"label": _("Documents"),
			"items": [
				{"type": "doctype", "name": "Job Card", "description": _("Job Card.")},
				{"type": "doctype", "name": "Requested Items", "description": _("Requested Items.")},
				{"type": "doctype", "name": "Workshop Request", "description": _("Workshop Request.")},
			],
		},
		{
			"label": _("Setup"),
			"items": [
				{
					"type": "doctype",
					"name": "Workshop Service Type",
					"description": _("Workshop Service Type"),
				},
				{"type": "doctype", "name": "Workshop Service", "description": _("Workshop Service")},
			],
		},
		{
			"label": _("Reports"),
			"items": [
				{
					"type": "report",
					"name": "Workshop Daily Report",
					"doctype": "Job Card",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Workshop Report",
					"doctype": "Job Card",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Unprocessed Workshop Requests",
					"doctype": "Workshop Request",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Used Items Report",
					"doctype": "Job Card",
					"is_query_report": True,
				},
			],
		},
	]
