"""Retire the modules csf_tz no longer ships, without destroying data that is still in use."""

import os

import frappe
from frappe.installer import (
	_delete_linked_documents,
	_get_module_linked_doctype_field_map,
)

APP_NAME = "csf_tz"

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
	"""Drop the metadata and tables of the retired modules, skipping anything still in use.

	A DocType is kept when it still holds records, or when another installed app now ships it -
	`Shipping Line` belongs to the `clearing` app on Tanzania sites and its table is shared. A
	module is only unregistered once every one of its doctypes has been removed.
	"""
	owners = get_doctypes_shipped_by_other_apps()

	for module in get_retired_modules():
		module_names = {module, *MODULE_ALIASES.get(module, ())}
		kept = remove_doctypes(module_names, owners)

		if kept:
			frappe.logger().warning(f"{APP_NAME}: kept module {module}, still used by {', '.join(kept)}")
			continue

		remove_module_records(module_names)
		frappe.db.delete("Module Def", {"name": module})

	frappe.clear_cache()


def get_retired_modules():
	return frappe.get_all(
		"Module Def",
		filters={"name": ["in", REMOVED_MODULES], "app_name": APP_NAME},
		pluck="name",
	)


def get_doctypes_shipped_by_other_apps():
	"""Map a scrubbed doctype name to the installed app, other than csf_tz, that ships it."""
	owners = {}
	for app in frappe.get_installed_apps():
		if app == APP_NAME:
			continue

		for module in frappe.get_module_list(app):
			folder = frappe.get_app_path(app, frappe.scrub(module), "doctype")
			if not os.path.isdir(folder):
				continue

			for slug in os.listdir(folder):
				if os.path.isfile(os.path.join(folder, slug, f"{slug}.json")):
					owners.setdefault(slug, app)

	return owners


def remove_doctypes(module_names, owners=None):
	"""Remove the module's doctypes and return the names of the ones that were kept."""
	if not module_names:
		return []

	if owners is None:
		owners = get_doctypes_shipped_by_other_apps()

	kept = []
	doctypes = frappe.get_all("DocType", filters={"module": ["in", tuple(module_names)]}, pluck="name")

	for doctype in doctypes:
		reason = get_reason_to_keep(doctype, owners)
		if reason:
			frappe.logger().warning(f"{APP_NAME}: keeping DocType {doctype}, {reason}")
			kept.append(doctype)
			continue

		remove_doctype_metadata(doctype)

	return kept


def get_reason_to_keep(doctype, owners):
	owner_app = owners.get(frappe.scrub(doctype))
	if owner_app:
		return f"shipped by {owner_app}"

	if not frappe.db.table_exists(doctype, cached=False):
		return None

	record_count = frappe.db.count(doctype)
	if record_count:
		return f"it holds {record_count} record(s)"

	return None


def remove_module_records(module_names):
	if not module_names:
		return

	doctype_link_field_map = _get_module_linked_doctype_field_map()
	for module in module_names:
		_delete_linked_documents(module, doctype_link_field_map, dry_run=False)


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
