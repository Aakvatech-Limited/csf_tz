# import frappe


def execute():
	from frappe import db

	db.set_single_value("Website Settings", "disable_signup", 1)
