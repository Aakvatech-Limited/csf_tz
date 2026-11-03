"""Regression coverage for the retained Import File feature and v16 repair patch."""

import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe
from frappe.core.doctype.doctype.doctype import validate_fields_for_doctype
from frappe.tests import IntegrationTestCase

from csf_tz.patches import restore_import_file
from csf_tz.patches.remove_deleted_modules_metadata import get_reason_to_keep, remove_doctypes


class TestImportFileCleanupGuard(TestCase):
	def test_empty_or_missing_import_file_is_preserved(self):
		with patch.object(frappe.db, "table_exists") as table_exists:
			self.assertIn("csf_tz", get_reason_to_keep("Import File", {}))
			table_exists.assert_not_called()

	def test_legacy_module_cleanup_does_not_delete_import_file(self):
		with (
			patch.object(frappe, "get_all", return_value=["Import File"]),
			patch("csf_tz.patches.remove_deleted_modules_metadata.remove_doctype_metadata") as delete,
		):
			self.assertEqual(remove_doctypes({"Clearing And Forwarding"}, {}), ["Import File"])
			delete.assert_not_called()

	def test_schema_has_only_standard_dependencies(self):
		path = Path(__file__).parents[1] / "csf_tz/doctype/import_file/import_file.json"
		schema = json.loads(path.read_text())
		self.assertEqual(schema["module"], "CSF TZ")
		self.assertEqual(
			{field["options"] for field in schema["fields"] if field["fieldtype"] == "Link"},
			{"Supplier", "Currency"},
		)

	def test_repair_loads_target_before_creating_links(self):
		meta = Mock()
		meta.has_field.return_value = True
		calls = Mock()
		with (
			patch.object(frappe, "reload_doc", calls.reload),
			patch.object(frappe, "clear_cache", calls.clear_cache),
			patch.object(frappe, "get_meta", return_value=meta),
			patch.object(restore_import_file, "create_custom_fields", calls.create),
		):
			restore_import_file.execute()
		self.assertEqual(calls.mock_calls[0][0], "reload")
		calls.reload.assert_called_once_with("csf_tz", "doctype", "import_file", force=True)
		fields = calls.create.call_args.args[0]
		self.assertEqual(set(fields), {"Purchase Invoice", "Journal Entry", "Landed Cost Voucher"})
		self.assertEqual(calls.create.call_args.kwargs, {"update": False})

	def test_repair_supports_sites_without_legacy_anchor_fields(self):
		meta = Mock()
		meta.has_field.return_value = False
		meta.fields = [Mock(fieldname="last_standard_field")]
		with (
			patch.object(frappe, "reload_doc"),
			patch.object(frappe, "clear_cache"),
			patch.object(frappe, "get_meta", return_value=meta),
			patch.object(restore_import_file, "create_custom_fields") as create,
		):
			restore_import_file.execute()
		for fields in create.call_args.args[0].values():
			self.assertEqual(fields[0]["insert_after"], "last_standard_field")


class TestRestoreImportFile(IntegrationTestCase):
	def test_patch_is_repeatable_and_preserves_records_and_customizations(self):
		restore_import_file.execute()
		name = "_Test Import File " + frappe.generate_hash(length=10)
		doc = frappe.get_doc(
			{"doctype": "Import File", "import_file_number": name, "supplier_invoice_no": "KEEP-ME"}
		).insert(ignore_permissions=True)
		try:
			links_before = self.get_links()
			restore_import_file.execute()
			restore_import_file.execute()
			self.assertEqual(frappe.db.get_value("Import File", doc.name, "supplier_invoice_no"), "KEEP-ME")
			self.assertEqual(frappe.get_meta("Import File").module, "CSF TZ")
			self.assertEqual(self.get_links(), links_before)
			for doctype in ("Purchase Invoice", "Journal Entry", "Landed Cost Voucher"):
				validate_fields_for_doctype(doctype)
		finally:
			# reload_doc may issue DDL and commit; explicitly remove the test document.
			frappe.delete_doc("Import File", doc.name, ignore_permissions=True)
			frappe.db.commit()

	def get_links(self):
		links = {}
		for doctype in ("Purchase Invoice", "Journal Entry", "Landed Cost Voucher"):
			fields = frappe.get_all(
				"Custom Field",
				filters={"dt": doctype, "fieldname": "import_file"},
				fields=["name", "fieldtype", "options", "insert_after", "allow_on_submit"],
			)
			self.assertEqual(len(fields), 1)
			self.assertEqual(fields[0].fieldtype, "Link")
			self.assertEqual(fields[0].options, "Import File")
			links[doctype] = dict(fields[0])
		return links
