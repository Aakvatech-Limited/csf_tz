import frappe

def execute():
    if not frappe.db.exists("DocType", "Log Settings"):
        return

    log_settings = frappe.get_doc("Log Settings")

    if not any(d.ref_doctype == "Vehicle Sync Task" for d in log_settings.logs_to_clear):
        log_settings.append("logs_to_clear", {
            "ref_doctype": "Vehicle Sync Task",
            "days": 7
        })

    log_settings.save(ignore_permissions=True)
