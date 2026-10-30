"""Offline contract tests: never contact the live Pergamon endpoint."""

from datetime import datetime
from unittest.mock import Mock, patch

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

	def test_current_timestamp_is_not_sales_invoice_posting_date(self):
		doc = self.make_invoice()
		doc.posting_date = "2025-01-01"
		doc.posting_time = "01:02:03"
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
			patch.object(pergamon, "now_datetime", return_value=datetime(2026, 10, 30, 20, 51, 9)),
		):
			payload = pergamon.get_payload(doc)
		self.assertEqual(payload["dateTime"], "2026-10-30 20:51:09")
		self.assertEqual(doc.posting_date, "2025-01-01")

	def test_explicit_fiscal_timestamp_for_submission(self):
		self.assertEqual(
			pergamon.get_fiscal_datetime(datetime(2026, 10, 30, 20, 51, 9)),
			"2026-10-30 20:51:09",
		)

	def test_payload_contract(self):
		doc = self.make_invoice()
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
			patch.object(pergamon, "now_datetime", return_value=datetime(2026, 10, 30, 20, 51, 9)),
		):
			result = pergamon.get_payload(doc)
		self.assertEqual(result["traderInvoiceNo"], doc.name)
		self.assertEqual(result["totalAmount"], 50)
		self.assertEqual(result["salesItems"][0]["taxCode"], "A")
		self.assertEqual(result["salesItems"][0]["amount"], 50)
		self.assertEqual(result["custPhone"], "0768044059")

	def test_usd_invoice_uses_base_tzs_values(self):
		doc = self.make_invoice()
		doc.currency = "USD"
		doc.conversion_rate = 2500
		doc.grand_total = 2
		doc.base_grand_total = 50
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
		):
			result = pergamon.get_payload(doc)
		self.assertEqual(result["totalAmount"], 50)
		self.assertEqual(result["currency"], "TZS")
		self.assertEqual(result["exchangeRate"], 1)
		self.assertEqual(result["salesItems"][0]["unitPrice"], 50)

	def test_six_zero_rated_usd_lines_in_tzs(self):
		doc = self.make_invoice()
		doc.name = "ACC-SINV-2026-00080"
		doc.company = "R&K Trucking Company"
		doc.currency = "USD"
		doc.conversion_rate = 2646
		doc.grand_total = 960
		doc.base_grand_total = 2540160
		doc.vfd_cust_id = "999999999.0"
		doc.posting_date = "2026-10-29"
		doc.posting_time = "12:53:17.300057"
		doc.items = [
			frappe._dict({
				"item_code": "STO-ITEM-2026-00367",
				"item_name": "Transit Transportation",
				"item_tax_template": "ZERO-RATED",
				"qty": 1,
				"base_rate": 423360,
				"base_amount": 423360,
				"base_net_amount": 423360,
			}) for _ in range(6)
		]
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=3),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
		):
			payload = pergamon.get_payload(doc)
		self.assertEqual(payload["totalAmount"], 2540160)
		self.assertEqual(payload["currency"], "TZS")
		self.assertEqual(payload["exchangeRate"], 1)
		self.assertEqual(payload["custId"], "999999999")
		self.assertEqual(payload["dateTime"], "2026-10-30 20:51:09")
		self.assertEqual(len(payload["salesItems"]), 6)
		self.assertTrue(all(line["amount"] == 423360 and line["taxCode"] == "C" for line in payload["salesItems"]))

	def test_six_standard_rated_tzs_lines_round_to_invoice_total(self):
		"""ACC-SINV-2026-00077: six base rates plus 18% VAT and rounding."""
		doc = self.make_invoice()
		doc.name = "ACC-SINV-2026-00077"
		doc.customer_name = "Export Trading Co. Ltd"
		doc.vfd_cust_id = "125082890.0"
		doc.posting_date = "2026-10-29"
		doc.posting_time = "11:42:3.181251"
		doc.base_grand_total = 2699999.98
		doc.base_rounded_total = 2700000
		doc.base_rounding_adjustment = 0.02
		doc.items = [
			frappe._dict(
				{
					"item_code": "STO-ITEM-2026-00366",
					"item_name": "Local Transportation",
					"item_tax_template": "STANDARD-VAT",
					"qty": 1,
					"base_rate": 381355.93,
					"base_amount": 381355.93,
					"base_net_amount": 381355.93,
					"distributed_discount_amount": 0,
				}
			)
			for _ in range(6)
		]
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
		):
			payload = pergamon.get_payload(doc)
		self.assertEqual(payload["totalAmount"], 2700000)
		self.assertEqual(payload["currency"], "TZS")
		self.assertEqual(payload["custId"], "125082890")
		self.assertEqual(payload["dateTime"], "2026-10-30 20:51:09")
		self.assertEqual(len(payload["salesItems"]), 6)
		self.assertTrue(all(row["taxCode"] == "A" and row["amount"] == 450000 for row in payload["salesItems"]))

	def test_inconsistent_base_rounding_is_rejected(self):
		doc = self.make_invoice()
		doc.base_rounded_total = 51
		with patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"):
			self.assertRaises(frappe.ValidationError, pergamon.get_payload, doc)

	def test_rejects_non_tzs_company_base_currency(self):
		doc = self.make_invoice()
		with patch.object(pergamon.frappe, "get_cached_value", return_value="USD"):
			self.assertRaises(frappe.ValidationError, pergamon.get_payload, doc)

	def test_all_five_tax_codes(self):
		doc = self.make_invoice()
		doc.items = [
			frappe._dict(
				dict(
						doc.items[0],
						item_code=str(i),
						base_rate=10,
						base_amount=10,
						base_net_amount=(8.47 if i == 1 else 10),
					)
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

	def test_customer_vfd_identifiers_are_used(self):
		doc = self.make_invoice()
		doc.vfd_cust_id_type = "1- TIN"
		doc.vfd_cust_id = "125082890.0"
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
		):
			payload = pergamon.get_payload(doc)
		self.assertEqual(payload["custIdType"], "1")
		self.assertEqual(payload["custId"], "125082890")

	def test_missing_customer_vfd_identifiers_are_rejected(self):
		doc = self.make_invoice()
		with patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"):
			doc.vfd_cust_id_type = ""
			self.assertRaises(frappe.ValidationError, pergamon.get_payload, doc)
			doc.vfd_cust_id_type = "1- TIN"
			doc.vfd_cust_id = ""
			self.assertRaises(frappe.ValidationError, pergamon.get_payload, doc)

	def test_verification_url_in_nested_success_response(self):
		response = {
			"success": True,
			"data": {
				"verificationCode": "VFD-2026-42",
				"verificationUrl": "https://verify.tra.go.tz/example",
			},
		}
		accepted, receipt = pergamon.parse_receipt(response)
		self.assertTrue(accepted)
		self.assertEqual(
			pergamon.receipt_field(receipt, "verificationUrl", "traReceiptVerificationUrl"),
			"https://verify.tra.go.tz/example",
		)

	def test_verification_url_in_result_envelope(self):
		response = {
			"status": "SUCCESS",
			"result": {
				"traReceiptVerificationCode": "VFD-2026-42",
				"traReceiptVerificationUrl": "https://verify.tra.go.tz/another",
			},
		}
		accepted, receipt = pergamon.parse_receipt(response)
		self.assertTrue(accepted)
		self.assertEqual(
			pergamon.receipt_field(receipt, "verificationUrl", "traReceiptVerificationUrl"),
			"https://verify.tra.go.tz/another",
		)

	def test_missing_verification_url_does_not_invent_one(self):
		response = {"success": True, "verificationCode": "VFD-2026-42"}
		self.assertTrue(pergamon.parse_receipt(response)[0])
		self.assertIsNone(
			pergamon.receipt_field(response, "verificationUrl", "traReceiptVerificationUrl")
		)

	def test_failed_invoice_can_use_normal_vfd_retry(self):
		doc = self.make_invoice()
		doc.docstatus = 1
		doc.is_return = 0
		doc.is_not_vfd_invoice = 0
		doc.vfd_status = "Failed"
		pergamon.validate_postable(doc)

	def test_successful_invoice_cannot_be_resent(self):
		doc = self.make_invoice()
		doc.docstatus = 1
		doc.is_return = 0
		doc.is_not_vfd_invoice = 0
		doc.vfd_status = "Success"
		self.assertRaises(frappe.ValidationError, pergamon.validate_postable, doc)

	def test_invoice_lookup_matches_reference_amount_and_verification(self):
		doc = self.make_invoice()
		response = Mock(ok=True, status_code=200)
		response.json.return_value = {
			"data": {
				"traderInvoiceNo": doc.name,
				"totalAmount": 50,
				"verificationCode": "VFD-123",
				"verificationUrl": "https://example.org/verify",
			}
		}
		provider = Mock(name="Pergamon")
		provider.name = "Pergamon"
		provider.sandbox = 0
		provider.base_url = "https://example.org/api/v1"
		provider.get_endpoint.return_value = "/invoices/{id}"
		settings = Mock(username="test")
		settings.get_password.return_value = "test-password"
		with (
			patch.object(pergamon.frappe, "get_doc", side_effect=[doc, settings]),
			patch.object(pergamon, "get_provider", return_value=provider),
			patch.object(pergamon.frappe.db, "get_value", return_value="Pergamon"),
			patch.object(pergamon.requests, "get", return_value=response) as get,
			patch.object(doc, "check_permission", create=True),
		):
			result = pergamon.get_pergamon_invoice("123", sales_invoice=doc.name)
		self.assertTrue(result["verified"])
		self.assertEqual(result["verification_code"], "VFD-123")
		self.assertEqual(get.call_args.args[0], "https://example.org/api/v1/invoices/123")

	def test_invoice_lookup_rejects_invalid_id(self):
		self.assertRaises(frappe.ValidationError, pergamon.get_pergamon_invoice, "../123", "SINV-1")

	def test_invoice_lookup_requires_linked_sales_invoice(self):
		self.assertRaises(frappe.ValidationError, pergamon.get_pergamon_invoice, "123")


	def test_amount_mismatch_is_rejected(self):
		doc = self.make_invoice()
		doc.base_grand_total = 100
		with (
			patch.object(pergamon, "get_item_taxcode", return_value=1),
			patch.object(pergamon.frappe, "get_cached_value", return_value="TZS"),
		):
			self.assertRaises(frappe.ValidationError, pergamon.get_payload, doc)
