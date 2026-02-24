import frappe

def execute():
    frappe.db.set_value("Custom Field", "Employee-bank_country_code", "options", "") 
    frappe.db.set_value("Custom Field", "Employee-employee_country", "fetch_from", "") 
    frappe.db.commit()
