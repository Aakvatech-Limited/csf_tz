import frappe


def execute():
    field = "Landed Cost Voucher-foreign_import_trackers"
    if frappe.db.get_value("Custom Field", field, "options") != "LCV Import Tracker Link":
        return

    target = "Foreign Import LCV Details"
    if not frappe.db.get_value("DocType", target, "istable"):
        frappe.throw(f"Required child DocType {target} is missing or invalid")

    frappe.db.set_value("Custom Field", field, "options", target)
    frappe.clear_cache(doctype="Landed Cost Voucher")
