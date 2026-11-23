from frappe import _


def get_data():
	return {
		"fieldname": "import",
		"non_standard_fieldnames": {
			"Files": "import_reference",
			"Transport Request": "reference_docname",
			"Requested Payments": "reference_docname",
			"Landed Cost Voucher": "receipt_document",
			"Purchase Invoice": "return_against",
		},
		"internal_links": {
			#'Purchase Order': ['items', 'purchase_order'],
			#'Purchase Receipt': ['items', 'purchase_receipt'],
		},
		"transactions": [
			{"label": _("References"), "items": ["Files", "Transport Request", "Requested Payments"]},
		],
	}
