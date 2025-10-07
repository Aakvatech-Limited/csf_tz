import frappe

def execute():
    frappe.db.sql("""
        DELETE FROM `tabVersion` 
        WHERE ref_doctype IN ('Vehicle Fine Record', 'Parking Bill')
    """)
    
    frappe.db.commit()
