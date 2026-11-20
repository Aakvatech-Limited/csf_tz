# installation_note_dashboard.py
from frappe import _


def get_data():
	return {
		"fieldname": "installation_note_dashboard",
		"non_standard_fieldnames": {
			"Delivery Note": "against_sales_invoice",
			"Journal Entry": "reference_name",
			"Payment Entry": "reference_name",
			"Payment Request": "reference_name",
			"Auto Repeat": "reference_document",
		},
		"internal_links": {
			"Sales Invoice": ["readings", "sales_invoice"],
			"Sales Order": ["items", "sales_order"],
		},
		"transactions": [
			{"label": _("Reference"), "items": ["Sales Invoice", "Delivery Note", "Sales Order"]},
			{"label": _("Payment"), "items": ["Payment Entry", "Payment Request", "Journal Entry"]},
			{"label": _("Subscription"), "items": ["Auto Repeat"]},
		],
	}
