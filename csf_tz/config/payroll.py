from frappe import _


def get_data():
	return [
		{
			"label": _("Piecework"),
			"items": [
				{"label": "Piecework Type", "name": "Piecework Type", "type": "doctype"},
				{"label": "Piecework", "name": "Piecework", "type": "doctype"},
			],
		}
	]
