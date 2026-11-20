# import frappe


def execute():
	from frappe import db

	db.set_value("Website Settings", None, "disable_signup", 1)
