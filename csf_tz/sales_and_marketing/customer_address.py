import frappe
from frappe.query_builder.functions import Concat


def get_customer_address(customer):
	"""Return `customer_address` and `contact` of the customer's first Address, or None."""
	# get_value turns a None filter into IS NULL; the original `= NULL` never matched.
	if customer is None:
		return None

	address_name = frappe.db.get_value(
		"Dynamic Link",
		{"parenttype": "Address", "link_doctype": "Customer", "link_name": customer},
		"parent",
		order_by="creation asc",
	)
	if not address_name:
		return None

	address = frappe.qb.DocType("Address")
	rows = (
		frappe.qb.from_(address)
		.select(
			Concat(address.address_line1, ",", address.city, ",", address.country).as_("customer_address"),
			address.phone.as_("contact"),
		)
		.where(address.name == address_name)
		.run(as_dict=True)
	)
	return rows[0] if rows else None
