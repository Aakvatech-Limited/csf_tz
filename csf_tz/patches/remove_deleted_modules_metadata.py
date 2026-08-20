import frappe
from frappe.installer import (
	_delete_linked_documents,
	_get_module_linked_doctype_field_map,
)

REMOVED_MODULES = (
	"After Sales Services",
	"Clearing And Forwarding",
	"Fleet Management",
	"Workshop",
)

MODULE_ALIASES = {
	"Clearing And Forwarding": ("Clearing and Forwarding",),
}


def execute():
	modules = frappe.get_all(
		"Module Def",
		filters={"name": ["in", REMOVED_MODULES], "app_name": "csf_tz"},
		pluck="name",
	)

	module_names = set(modules)
	for module in modules:
		module_names.update(MODULE_ALIASES.get(module, ()))

	remove_module_records(module_names)
	remove_doctypes(module_names)
	remove_modules(modules)

	frappe.clear_cache()


def remove_module_records(module_names):
	if not module_names:
		return

	doctype_link_field_map = _get_module_linked_doctype_field_map()
	for module in module_names:
		_delete_linked_documents(module, doctype_link_field_map, dry_run=False)


def remove_doctypes(module_names):
	if not module_names:
		return

	doctypes = frappe.get_all("DocType", filters={"module": ["in", tuple(module_names)]}, pluck="name")
	for doctype in doctypes:
		remove_doctype_metadata(doctype)


def remove_doctype_metadata(doctype):
	for child_table in ("DocField", "DocPerm", "DocType Action", "DocType Link", "DocType State"):
		frappe.db.delete(child_table, {"parent": doctype})

	frappe.db.delete("Custom Field", {"dt": doctype})
	frappe.db.delete("Custom Field", {"options": doctype})
	frappe.db.delete("DocField", {"options": doctype})
	frappe.db.delete("DocType Link", {"link_doctype": doctype})
	frappe.db.delete("Property Setter", {"doc_type": doctype})
	frappe.db.delete("User Permission", {"allow": doctype})
	frappe.db.delete("User Permission", {"applicable_for": doctype})
	frappe.db.delete("DocType", {"name": doctype})

	if frappe.db.table_exists(doctype, cached=False):
		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{doctype}`")


def remove_modules(modules):
	for module in modules:
		frappe.db.delete("Module Def", {"name": module})
