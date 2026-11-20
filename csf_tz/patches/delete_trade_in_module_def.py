import frappe


def execute():
    if frappe.db.get_value("Module Def", "Trade In", "app_name") == "csf_tz":
        frappe.delete_doc("Module Def", "Trade In", force=True, ignore_missing=True)
