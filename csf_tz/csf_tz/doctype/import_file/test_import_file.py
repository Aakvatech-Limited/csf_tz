"""Regression checks for the Import File feature retained inside csf_tz."""

import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.patches.remove_deleted_modules_metadata import get_reason_to_keep
from csf_tz.patches.restore_import_file import execute as restore_import_file


class TestImportFile(FrappeTestCase):
	def test_owned_by_csf_tz(self):
		meta = frappe.get_meta("Import File")
		self.assertEqual(meta.module, "CSF TZ")
		self.assertEqual(meta.autoname, "field:import_file_number")
		self.assertTrue(meta.has_field("import_file_number"))
		self.assertTrue(meta.has_field("supplier_name"))
		self.assertTrue(meta.has_field("invoice_currency"))
		self.assertTrue(meta.has_field("invoice_amount"))

	def test_create_and_reopen_preserves_document_name(self):
		name = "TEST-IMPORT-FILE-" + frappe.generate_hash(length=10)
		doc = frappe.get_doc(
			{
				"doctype": "Import File",
				"import_file_number": name,
				"bl_number": "BL-TEST",
				"invoice_amount": 150,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.name, name)
		loaded = frappe.get_doc("Import File", name)
		self.assertEqual(loaded.bl_number, "BL-TEST")
		self.assertEqual(loaded.invoice_amount, 150)

	def test_restore_patch_keeps_records_and_links(self):
		name = "TEST-IMPORT-FILE-" + frappe.generate_hash(length=10)
		frappe.get_doc({"doctype": "Import File", "import_file_number": name}).insert(
			ignore_permissions=True
		)
		restore_import_file()
		restore_import_file()
		self.assertTrue(frappe.db.exists("Import File", name))
		for doctype in ("Purchase Invoice", "Journal Entry", "Landed Cost Voucher"):
			field = frappe.get_meta(doctype).get_field("import_file")
			self.assertIsNotNone(field, doctype)
			self.assertEqual(field.fieldtype, "Link")
			self.assertEqual(field.options, "Import File")

	def test_retired_module_cleanup_exempts_import_file(self):
		self.assertIsNotNone(get_reason_to_keep("Import File", {}))
