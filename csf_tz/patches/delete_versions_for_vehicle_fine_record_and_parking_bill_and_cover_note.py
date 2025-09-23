import frappe

def execute():
    for doctype in ["Vehicle Fine Record", "Parking Bill", "TZ Insurance Cover Note"]:
        versions = frappe.get_all("Version", filters={"ref_doctype": doctype}, pluck="name")
        for version_name in versions:
            frappe.delete_doc("Version", version_name, force=1)
    frappe.db.commit()
