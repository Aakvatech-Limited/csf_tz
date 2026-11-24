from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from csf_tz.patches import setup_default_vfd_providers


class TestDefaultVFDProviders(FrappeTestCase):
	def test_missing_providers_are_created_once(self):
		existing = {"TotalVFD"}
		records = []

		def exists(doctype, filters):
			self.assertEqual(doctype, "VFD Provider")
			return filters["vfd_provider"] in existing

		def get_doc(data):
			doc = Mock()

			def insert(**kwargs):
				self.assertTrue(kwargs["ignore_permissions"])
				records.append(data)
				existing.add(data["vfd_provider"])

			doc.insert.side_effect = insert
			return doc

		with (
			patch.object(setup_default_vfd_providers.frappe.db, "exists", side_effect=exists),
			patch.object(setup_default_vfd_providers.frappe, "get_doc", side_effect=get_doc),
		):
			setup_default_vfd_providers.execute()
			setup_default_vfd_providers.execute()

		self.assertEqual([row["vfd_provider"] for row in records], ["VFDPlus", "SimplifyVFD"])
		self.assertEqual([len(row["attributes"]) for row in records], [4, 3])
		for row in records:
			self.assertTrue(row["vfd_provider_controller"].startswith("csf_tz.vfd_providers."))
			self.assertEqual(
				set(row),
				{
					"doctype", "vfd_provider", "vfd_provider_settings",
					"vfd_provider_controller", "base_url", "attributes",
				},
			)

	def test_total_vfd_defaults(self):
		with (
			patch.object(setup_default_vfd_providers.frappe.db, "exists", return_value=False),
			patch.object(setup_default_vfd_providers.frappe, "get_doc") as get_doc,
		):
			setup_default_vfd_providers.execute()
		self.assertEqual(get_doc.call_count, 3)
		total = get_doc.call_args_list[0].args[0]
		self.assertEqual(total["base_url"], "https://api.totalvfd.co.tz")
		self.assertEqual(total["attributes"], [{"key": "sales", "value": "/sales"}])
