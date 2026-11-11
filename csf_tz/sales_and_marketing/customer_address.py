import frappe
from frappe.query_builder.functions import Concat


def get_customer_address_name(customer):
	dynamic_link = frappe.qb.DocType("Dynamic Link")
	return (
		frappe.qb.from_(dynamic_link)
		.select(dynamic_link.parent)
		.where(dynamic_link.parenttype == 'Address')
		.where(dynamic_link.link_doctype == 'Customer')
		.where(dynamic_link.link_name == customer)
		.orderby(dynamic_link.creation)
		.limit(1)
		.run(as_dict=True)
	)


def get_address_details(address_name):
	address = frappe.qb.DocType("Address")
	return (
		frappe.qb.from_(address)
		.select(
			Concat(address.address_line1, ",", address.city, ',', address.country).as_("customer_address"),
			address.phone.as_("contact"),
		)
		.where(address.name == address_name)
		.run(as_dict=True)
	)
