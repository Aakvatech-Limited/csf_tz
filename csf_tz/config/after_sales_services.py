from frappe import _


def get_data():
	return [
		{
			"label": _("After Sales"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Delivery Note",
					"description": _("Delivery Note"),
				},
				{
					"type": "doctype",
					"name": "Installation Note",
					"description": _("Items Installation Notes"),
				},
				{
					"type": "doctype",
					"name": "Pre Delivery Inspection",
					"description": _("Pre-delivery Inspection"),
				},
				{
					"type": "doctype",
					"name": "Registration Card Management Module",
					"label": "Registration Card Transfer Management",
					"description": _("Registration Card Transfer Procedures."),
				},
			],
		},
		{
			"label": _("Maintenance"),
			"icon": "fa fa-star",
			"items": [
				{"type": "doctype", "name": "Maintenance Request", "description": _("Maintenance Request.")},
				{"type": "doctype", "name": "Job Card", "description": _("Job Card.")},
				{
					"type": "doctype",
					"name": "Warranty Claim",
					"description": _("Warranty Claim against Serial No."),
				},
				{"type": "doctype", "name": "Requested Items", "description": _("Requested Items")},
			],
		},
		{
			"label": _("Machine Stripping"),
			"items": [
				{"type": "doctype", "name": "Machine Strip Request", "description": "Machine Strip Request"}
			],
		},
		{
			"label": _("After Sales Reports"),
			"items": [
				{
					"type": "report",
					"name": "Delivery Note Report",
					"doctype": "Delivery Note",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Pre Delivery Inspection Report",
					"doctype": "Pre Delivery Inspection",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Installation Note Report",
					"doctype": "Installation Note",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Technician Costing Report",
					"doctype": "Job Card",
					"is_query_report": True,
				},
			],
		},
		{
			"label": _("Workshop Reports"),
			"items": [
				{
					"type": "report",
					"name": "Maintenance Daily Report",
					"doctype": "Job Card",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Maintenance Report",
					"doctype": "Job Card",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Unprocessed Maintenance Requests",
					"doctype": "Maintenance Request",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Used Items Report",
					"doctype": "Job Card",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Maintenance Request Report",
					"doctype": "Maintenance Request",
					"is_query_report": True,
				},
			],
		},
		{
			"label": _("Workshop Performance Analysis"),
			"items": [
				{
					"type": "report",
					"name": "Technicians Performance Report",
					"doctype": "Job Card",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Workshop Performance Report",
					"doctype": "Job Card",
					"is_query_report": True,
				},
			],
		},
		{
			"label": _("Setup"),
			"items": [
				{
					"type": "doctype",
					"name": "Maintenance Service Type",
					"description": _("Maintenance Service Type"),
				},
				{"type": "doctype", "name": "Maintenance Service", "description": _("Maintenance Service")},
				{
					"type": "doctype",
					"name": "Item Installation Procedures",
					"label": _("Installation Procedures"),
					"description": _("Item Installation Procedures"),
				},
				{
					"type": "doctype",
					"name": "Pre Delivery Inspection Template",
					"description": _("Pre-delivery Inspection Template"),
				},
			],
		},
	]
