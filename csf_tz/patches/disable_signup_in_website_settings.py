import frappe


def execute():
	frappe.db.set_single_value("Website Settings", "disable_signup", 1)
