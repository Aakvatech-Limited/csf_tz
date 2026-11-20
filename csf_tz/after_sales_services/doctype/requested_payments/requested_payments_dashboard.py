from frappe import _


def get_data():
	return {
		"fieldname": "re",
		"non_standard_fieldnames": {"Payment Entry": "reference_name"},
		"internal_links": {"Sales Order": ["references", "reference_name"]},
		"transactions": [{"label": _("Payments"), "items": ["Payment Entry"]}],
	}
