from frappe import _


def get_data():
	return [
		{
			"label": _("Stock Transactions"),
			"items": [
				{
					"type": "doctype",
					"name": "Special Closing Balance",
					"doctype": "Special Closing Balance",
					"description": _(
						"Enter closing balances and it will create Material Receipt type Stock Entry, to avoid manufacturing and remake entries."
					),
					"dependencies": ["Item", "Warehouse"],
				},
			],
		},
	]
