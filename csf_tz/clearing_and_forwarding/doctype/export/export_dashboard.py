from frappe import _


def get_data():
	return {
		"fieldname": "export",
		"non_standard_fieldnames": {
			"Files": "export_reference",
			"Requested Payments": "reference_docname",
		},
		"internal_links": {
			#'Purchase Order': ['items', 'purchase_order'],
			#'Purchase Receipt': ['items', 'purchase_receipt'],
		},
		"transactions": [
			{"label": _("Reference"), "items": ["Files", "Requested Payments"]},
		],
	}
