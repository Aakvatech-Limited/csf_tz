import frappe

MODULES = ("VFD Providers", "VFD Settings")
APP_NAME = "csf_tz"


def execute():
	for module_name in MODULES:
		if frappe.db.exists("Module Def", module_name):
			frappe.db.set_value("Module Def", module_name, "app_name", APP_NAME, update_modified=False)
