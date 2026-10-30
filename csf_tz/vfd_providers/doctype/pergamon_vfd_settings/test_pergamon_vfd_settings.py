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
				"posting_date": "2026-10-30",
				"posting_time": "05:01:15",
				"items": [
					frappe._dict(
						{
							"item_code": "ITEM-A",
							"item_name": "Item A",
							"item_tax_template": "VAT-A",
							"qty": 1,
						}
					),
				],
			}
		)

	def test_payload_contract(self):
		doc = self.make_invoice()
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon, "get_vat_amount", return_value=50),
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
			patch.object(pergamon, "get_vat_amount", return_value=5000),
		):
			result = pergamon.get_payload(doc)
		self.assertEqual(result["totalAmount"], 2)
		self.assertEqual(result["exchangeRate"], 2500)

	def test_all_five_tax_codes(self):
		doc = self.make_invoice()
		doc.items = [frappe._dict(dict(doc.items[0], item_code=str(i))) for i in range(1, 6)]
		doc.grand_total = 50
		with (
			patch.object(pergamon, "get_item_taxcode", side_effect=[1, 2, 3, 4, 5]),
			patch.object(pergamon, "get_vat_amount", return_value=10),
		):
			result = pergamon.get_payload(doc)
		self.assertEqual([row["taxCode"] for row in result["salesItems"]], list("ABCDE"))

	def test_unknown_response_never_marks_fiscal_success(self):
		self.assertFalse(pergamon.parse_receipt({"message": "OK"})[0])
		self.assertFalse(pergamon.parse_receipt({"success": True})[0])
		self.assertTrue(pergamon.parse_receipt({"success": True, "verificationCode": "VERIFY-123"})[0])

	def test_amount_mismatch_is_rejected(self):
		doc = self.make_invoice()
		doc.grand_total = 100
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon, "get_vat_amount", return_value=50),
		):
			self.assertRaises(frappe.ValidationError, pergamon.get_payload, doc)
