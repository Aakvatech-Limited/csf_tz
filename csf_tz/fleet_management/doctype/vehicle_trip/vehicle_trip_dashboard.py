from frappe import _


def get_data():
	return {
		"fieldname": "purchase_invoice",
		"non_standard_fieldnames": {
			"Requested Payments": "reference_docname",
			"Fuel Request": "reference_docname",
			"Transport Assignment": "vehicle_trip",
		},
		"internal_links": {
			#'Purchase Order': ['items', 'purchase_order'],
			#'Purchase Receipt': ['items', 'purchase_receipt'],
		},
		"transactions": [
			{
				"label": _("Reference"),
				"items": ["Requested Payments", "Fuel Request", "Transport Assignment"],
			},
		],
	}
