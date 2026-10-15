import frappe


@frappe.whitelist()
def get_landed_cost_expenses(import_file=None):
	if not import_file:
		return

	je = frappe.qb.DocType("Journal Entry")
	jea = frappe.qb.DocType("Journal Entry Account")
	pi = frappe.qb.DocType("Purchase Invoice")
	pii = frappe.qb.DocType("Purchase Invoice Item")
	je_landed_cost = (
		frappe.qb.from_(je)
		.inner_join(jea)
		.on(jea.parent == je.name)
		.select(
			jea.account.as_("expense_account"),
			je.title.as_("description"),
			jea.debit.as_("amount"),
		)
		.where(je.import_file == import_file)
		.where(je.docstatus == 1)
		.where(jea.debit > 0)
		.run(as_dict=True)
	)
	pinv_landed_cost = (
		frappe.qb.from_(pi)
		.inner_join(pii)
		.on(pii.parent == pi.name)
		.select(
			pii.expense_account.as_("expense_account"),
			pi.title.as_("description"),
			pii.base_net_amount.as_("amount"),
		)
		.where(pi.import_file == import_file)
		.where(pi.docstatus == 1)
		.run(as_dict=True)
	)
	return je_landed_cost + pinv_landed_cost


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
