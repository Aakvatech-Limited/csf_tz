from frappe import _


def get_data():
	return {
		"fieldname": "files",
		"non_standard_fieldnames": {
			"Import": "reference_file_number",
			"Export": "file_number",
			"Transport Request": "file_number",
			"Sales Invoice": "reference_docname",
			"Purchase Invoice": "reference_docname",
			"Border Clearance": "file_number",
		},
		"internal_links": {},
		"transactions": [
			{
				"label": _("Service References"),
				"items": ["Import", "Export", "Transport Request", "Border Clearance"],
			},
			{"label": _("Order References"), "items": ["Sales Invoice", "Purchase Invoice"]},
		],
	}
