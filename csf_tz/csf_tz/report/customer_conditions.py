import frappe
from pypika.terms import ExistsCriterion


def get_customer_conditions(filters, gl_entry):
	"""GL Entry party conditions for customer group, territory, payment terms and sales partner."""
	conditions = []

	if filters.get("customer_group"):
		conditions.append(
			gl_entry.party.isin(get_customers_in_tree(filters, "Customer Group", "customer_group"))
		)

	if filters.get("territory"):
		conditions.append(gl_entry.party.isin(get_customers_in_tree(filters, "Territory", "territory")))

	if filters.get("payment_terms_template"):
		conditions.append(
			gl_entry.party.isin(
				get_parties_where("Customer", "payment_terms", filters.get("payment_terms_template"))
			)
		)

	if filters.get("sales_partner"):
		conditions.append(
			gl_entry.party.isin(
				get_parties_where("Customer", "default_sales_partner", filters.get("sales_partner"))
			)
		)

	return conditions


def get_parties_where(doctype, fieldname, value):
	party = frappe.qb.DocType(doctype)
	return frappe.qb.from_(party).select(party.name).where(party[fieldname] == value)


def get_customers_in_tree(filters, tree_doctype, fieldname):
	"""Customers whose `fieldname` is the filtered `tree_doctype` node or one below it."""
	lft, rgt = frappe.db.get_value(tree_doctype, filters.get(fieldname), ["lft", "rgt"])
	customer = frappe.qb.DocType("Customer")
	tree = frappe.qb.DocType(tree_doctype)
	return (
		frappe.qb.from_(customer)
		.select(customer.name)
		.where(
			ExistsCriterion(
				frappe.qb.from_(tree)
				.select(tree.name)
				.where((tree.lft >= lft) & (tree.rgt <= rgt) & (tree.name == customer[fieldname]))
			)
		)
	)


def get_sales_person_condition(filters, gl_entry):
	"""GL Entry has a voucher, against voucher or customer in the filtered sales person's team."""
	lft, rgt = frappe.db.get_value("Sales Person", filters.get("sales_person"), ["lft", "rgt"])
	sales_person = frappe.qb.DocType("Sales Person")
	sales_team = frappe.qb.DocType("Sales Team")
	sales_people_in_tree = (
		frappe.qb.from_(sales_person)
		.select(sales_person.name)
		.where((sales_person.lft >= lft) & (sales_person.rgt <= rgt))
	)
	return ExistsCriterion(
		frappe.qb.from_(sales_team)
		.select(sales_team.name)
		.where(
			sales_team.sales_person.isin(sales_people_in_tree)
			& (
				(
					(sales_team.parent == gl_entry.voucher_no)
					& (sales_team.parenttype == gl_entry.voucher_type)
				)
				| (
					(sales_team.parent == gl_entry.against_voucher)
					& (sales_team.parenttype == gl_entry.against_voucher_type)
				)
				| ((sales_team.parent == gl_entry.party) & (sales_team.parenttype == "Customer"))
			)
		)
	)
