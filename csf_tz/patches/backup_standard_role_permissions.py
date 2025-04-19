import frappe
import json

def execute():
    if frappe.db.exists("CSF TZ Permission Backup", "Accounts User"):
        return

    standard_roles = frappe.get_all("Role", filters={"is_custom": 0}, pluck="name")

    for role in standard_roles:
        permissions = frappe.get_all(
            "DocPerm",
            filters={"role": role},
            fields=["parent", "permlevel", "read", "write", "create", "delete"]
        )

        # Convert permissions list to a JSON string
        permissions_json = json.dumps(permissions)

        frappe.get_doc({
            "doctype": "CSF TZ Permission Backup",
            "role": role,
            "permissions": permissions_json  # Pass as a string, not a list
        }).insert(ignore_permissions=True)

    frappe.msgprint("ERPNext default permissions backed up successfully.")