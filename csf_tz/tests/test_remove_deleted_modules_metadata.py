# Copyright (c) 2026, Aakvatech and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from csf_tz.patches.remove_deleted_modules_metadata import (
	APP_NAME,
	REMOVED_MODULES,
	get_doctypes_shipped_by_other_apps,
	get_reason_to_keep,
)


class TestRemovedModuleGuards(IntegrationTestCase):
	"""Retiring a module must never drop a table another app owns or that still holds data."""

	def setUp(self):
		self.owners = get_doctypes_shipped_by_other_apps()
		self.addCleanup(frappe.db.rollback)

	def make_doctype(self, name):
		"""A custom DocType stands in for a retired one; its module folder is long gone.

		Creating one issues DDL, which commits, so rolling the transaction back is not enough
		to undo it. Drop it explicitly or the next run hits a duplicate entry.
		"""
		self.drop_doctype(name)
		self.addCleanup(self.drop_doctype, name)

		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": name,
				"module": "CSF TZ",
				"custom": 1,
				"fields": [{"fieldname": "title", "fieldtype": "Data", "label": "Title"}],
				"permissions": [{"role": "System Manager"}],
			}
		).insert(ignore_permissions=True)

	def drop_doctype(self, name):
		frappe.db.delete("DocType", {"name": name})
		frappe.db.delete("DocField", {"parent": name})
		frappe.db.delete("DocPerm", {"parent": name})
		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{name}`")
		frappe.db.commit()

	def test_csf_tz_is_never_its_own_owner(self):
		self.assertNotIn(APP_NAME, set(self.owners.values()))

	def test_doctype_shipped_by_another_app_is_kept(self):
		shipped_by_others = sorted(slug for slug, app in self.owners.items() if app != "frappe")
		self.assertTrue(shipped_by_others, "no other installed app ships a doctype")

		reason = get_reason_to_keep(frappe.unscrub(shipped_by_others[0]), self.owners)
		self.assertIsNotNone(reason)
		self.assertIn("shipped by", reason)

	def test_doctype_holding_records_is_kept(self):
		name = "CSF TZ Retired Guard Test"
		self.make_doctype(name)
		frappe.get_doc({"doctype": name, "title": "keep me"}).insert(ignore_permissions=True)

		reason = get_reason_to_keep(name, self.owners)
		self.assertIsNotNone(reason)
		self.assertIn("record(s)", reason)

	def test_empty_doctype_is_removable(self):
		name = "CSF TZ Retired Empty Test"
		self.make_doctype(name)

		self.assertIsNone(get_reason_to_keep(name, self.owners))

	def test_unknown_doctype_without_a_table_is_removable(self):
		self.assertIsNone(get_reason_to_keep("CSF TZ Retired Missing Table", self.owners))

	def test_shipping_line_is_protected_when_clearing_is_installed(self):
		if "clearing" not in frappe.get_installed_apps():
			self.skipTest("clearing app is not installed on this site")

		self.assertEqual(self.owners.get("shipping_line"), "clearing")

	def test_removed_modules_are_not_shipped_by_csf_tz(self):
		shipped = set(frappe.get_module_list(APP_NAME))
		for module in REMOVED_MODULES:
			with self.subTest(module=module):
				self.assertNotIn(module, shipped)
