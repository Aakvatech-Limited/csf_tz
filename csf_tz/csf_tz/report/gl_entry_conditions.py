import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)


def get_child_accounts_query(account):
	"""Names of `account` and every non-cancelled account below it in the tree."""
	lft, rgt = frappe.db.get_value("Account", account, ["lft", "rgt"])
	account_table = frappe.qb.DocType("Account")
	return (
		frappe.qb.from_(account_table)
		.select(account_table.name)
		.where((account_table.lft >= lft) & (account_table.rgt <= rgt) & (account_table.docstatus < 2))
	)


def get_party_conditions(filters, gl_entry):
	conditions = []
	if filters.get("group_by") == "Group by Party" and not filters.get("party_type"):
		conditions.append(gl_entry.party_type.isin(["Customer", "Supplier"]))

	if filters.get("party_type"):
		conditions.append(gl_entry.party_type == filters.party_type)

	if filters.get("party"):
		conditions.append(gl_entry.party.isin(filters.party))

	return conditions


def get_posting_date_conditions(filters, gl_entry):
	conditions = []
	if not (
		filters.get("account")
		or filters.get("party")
		or filters.get("group_by") in ["Group by Account", "Group by Party"]
	):
		conditions.append(gl_entry.posting_date >= filters.from_date)

	conditions.append((gl_entry.posting_date <= filters.to_date) | (gl_entry.is_opening == "Yes"))
	return conditions


def get_finance_book_condition(filters, gl_entry):
	if filters.get("include_default_book_entries"):
		return (
			gl_entry.finance_book.isin([filters.finance_book, filters.company_fb, ""])
			| gl_entry.finance_book.isnull()
		)

	return gl_entry.finance_book.isin([filters.finance_book])


def get_dimension_conditions(filters, gl_entry):
	conditions = []
	for dimension in get_accounting_dimensions(as_list=False):
		if not filters.get(dimension.fieldname):
			continue

		if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
			filters[dimension.fieldname] = get_dimension_with_children(
				dimension.document_type, filters.get(dimension.fieldname)
			)
			conditions.append(gl_entry[dimension.fieldname].isin(filters[dimension.fieldname]))
		else:
			dimension_values = filters.get(dimension.fieldname)
			if isinstance(dimension_values, str):
				dimension_values = [dimension_values]
			conditions.append(gl_entry[dimension.fieldname].isin(dimension_values))

	return conditions
