"""Offline contract tests: never contact the live Pergamon endpoint."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.vfd_providers.doctype.pergamon_vfd_settings import pergamon_vfd_settings as pergamon


class TestPergamonVFDSettings(FrappeTestCase):
	def make_invoice(self):
		return frappe._dict(
			{
				"name": "SINV-TEST-0001",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"customer_name": "Customer",
				"vfd_cust_id_type": "1- TIN",
				"vfd_cust_id": "123456789",
				"contact_mobile": "0768 044 059",
				"currency": "TZS",
				"conversion_rate": 1,
				"grand_total": 50,
				"base_grand_total": 50,
				"posting_date": "2026-10-30",
				"posting_time": "05:01:15",
				"items": [
					frappe._dict(
						{
							"item_code": "ITEM-A",
							"item_name": "Item A",
							"item_tax_template": "VAT-A",
							"qty": 1,
							"base_rate": 50,
							"base_amount": 50,
							"base_net_amount": 42.37,
							"distributed_discount_amount": 0,
						}
					),
				],
			}
		)

	def test_payload_contract(self):
		doc = self.make_invoice()
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
		):
			result = pergamon.get_payload(doc)
		self.assertEqual(result["traderInvoiceNo"], doc.name)
		self.assertEqual(result["totalAmount"], 50)
		self.assertEqual(result["salesItems"][0]["taxCode"], "A")
		self.assertEqual(result["salesItems"][0]["amount"], 50)
		self.assertEqual(result["custPhone"], "0768044059")

	def test_currency_conversion_not_applied_twice(self):
		doc = self.make_invoice()
		doc.currency = "USD"
		doc.conversion_rate = 2500
		doc.grand_total = 2
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
		):
			result = pergamon.get_payload(doc)
		self.assertEqual(result["totalAmount"], 50)
		self.assertEqual(result["currency"], "TZS")
		self.assertEqual(result["exchangeRate"], 1)

	def test_all_five_tax_codes(self):
		doc = self.make_invoice()
		doc.items = [
			frappe._dict(
				dict(doc.items[0], item_code=str(i), base_rate=10, base_amount=10,
					base_net_amount=(8.47 if i == 1 else 10))
			)
			for i in range(1, 6)
		]
		doc.grand_total = 50
		with (
			patch.object(pergamon, "get_item_taxcode", side_effect=[1, 2, 3, 4, 5]),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
		):
			result = pergamon.get_payload(doc)
		self.assertEqual([row["taxCode"] for row in result["salesItems"]], list("ABCDE"))
		self.assertTrue(all(row["discount"] == 0 for row in result["salesItems"]))

	def test_vat_exclusive_adds_18_percent_to_base_rate(self):
		item = self.make_invoice().items[0]
		item.qty = 2
		item.base_rate = 100
		item.base_amount = 200
		item.base_net_amount = 200
		self.assertEqual(pergamon.get_line_amount(item, "A"), 236)

	def test_vat_inclusive_does_not_add_vat_twice(self):
		item = self.make_invoice().items[0]
		item.base_rate = 118
		item.base_amount = 118
		item.base_net_amount = 100
		self.assertEqual(pergamon.get_line_amount(item, "A"), 118)

	def test_other_tax_groups_use_base_rate_and_zero_vat(self):
		item = self.make_invoice().items[0]
		item.qty = 3
		item.base_rate = 10
		for group in "BCDE":
			self.assertEqual(pergamon.get_line_amount(item, group), 30)

	def test_unknown_response_never_marks_fiscal_success(self):
		self.assertFalse(pergamon.parse_receipt({"message": "OK"})[0])
		self.assertFalse(pergamon.parse_receipt({"success": True})[0])
		self.assertTrue(pergamon.parse_receipt({"success": True, "verificationCode": "VERIFY-123"})[0])

	def test_amount_mismatch_is_rejected(self):
		doc = self.make_invoice()
		doc.base_grand_total = 100
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
		):
			self.assertRaises(frappe.ValidationError, pergamon.get_payload, doc)
