import frappe

def execute():
    frappe.db.set_value("Custom Field", "Employee-bank_country_code", "options", "") 
    frappe.db.set_value("Custom Field", "Employee-employee_country", "fetch_from", "") 
    fields = ['employee_country', 'employee_country_code', 'bank_country', 'bank_country_code', 'beneficiary_bank_bic']
    for field in fields:
        frappe.db.delete("Custom Field", {"fieldname": field})
    frappe.db.commit()
