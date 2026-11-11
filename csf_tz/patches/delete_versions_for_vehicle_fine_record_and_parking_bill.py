import frappe

def execute():
    version = frappe.qb.DocType("Version")
    frappe.qb.from_(version).delete().where(
        version.ref_doctype.isin(["Vehicle Fine Record", "Parking Bill"])
    ).run()
   
    frappe.db.commit()