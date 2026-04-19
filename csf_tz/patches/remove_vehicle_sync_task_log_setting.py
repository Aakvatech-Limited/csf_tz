import frappe


def execute():
    if not frappe.db.exists("DocType", "Log Settings"):
        return

    log_settings = frappe.get_doc("Log Settings")
    rows_to_keep = [
        row for row in log_settings.logs_to_clear if row.ref_doctype != "Vehicle Sync Task"
    ]

    if len(rows_to_keep) == len(log_settings.logs_to_clear):
        return

    log_settings.set("logs_to_clear", rows_to_keep)
    log_settings.save(ignore_permissions=True)
