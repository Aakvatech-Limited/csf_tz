from frappe import _


def get_data():
	return {
		"fieldname": "border_processing",
		"non_standard_fieldnames": {
			"Requested Payments": "reference_docname",
			"Files": "border_processing_reference",
		},
		"transactions": [
			{"label": _("Reference"), "items": ["Requested Payments", "Files"]},
		],
	}
