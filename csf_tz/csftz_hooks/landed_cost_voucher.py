from __future__ import unicode_literals


def total_amount(doc, method):
	for item in doc.items:
		if item.amount and item.applicable_charges:
			item.custom_total_amount = item.amount + item.applicable_charges
		else:
			item.custom_total_amount = 0

	if doc.items:
		grand_total = 0
		for item in doc.items:
			grand_total += item.custom_total_amount or 0
		doc.custom_grand_total = grand_total
	else:
		doc.custom_grand_total = 0
