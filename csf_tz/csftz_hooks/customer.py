import frappe
from frappe import _
from frappe.query_builder.functions import Sum


@frappe.whitelist()
def get_customer_total_unpaid_amount(customer, company=None):
	if not customer:
		return 0

	frappe.has_permission("GL Entry", throw=True)
	gle = frappe.qb.DocType("GL Entry")
	query = (
		frappe.qb.from_(gle)
		.select(
			gle.company,
			(Sum(gle.debit_in_account_currency) - Sum(gle.credit_in_account_currency)).as_("balance"),
		)
		.where(gle.party_type == "Customer")
		.where(gle.party == customer)
		.where(gle.is_cancelled == 0)
		.groupby(gle.company)
	)
	if company:
		query = query.where(gle.company == company)

	balances = query.run(as_dict=True)
	total_unpaid = sum(row.balance or 0 for row in balances)
	formatted_total = frappe.format_value(total_unpaid, "Float")
	frappe.msgprint(_("Total Unpaid Amount is {0}").format(formatted_total))
	return formatted_total
