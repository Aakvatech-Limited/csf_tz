import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import add_days, add_to_date, get_datetime, now_datetime, nowdate

from csf_tz.tests.vfd_test_records import (
	COMPANY,
	EXEMPT_TEMPLATE,
	ITEM,
	PROVIDERS,
	SECOND_ITEM,
	SERIAL_INFO,
	fake_response,
	make_sales_invoice,
	make_vfd_records,
	set_company_provider,
)
from csf_tz.vfd_providers.doctype.simplify_vfd_settings import simplify_vfd_settings as simplify
from csf_tz.vfd_providers.doctype.total_vfd_setting import total_vfd_setting as total_vfd
from csf_tz.vfd_providers.doctype.vfdplus_settings import vfdplus_settings as vfdplus
from csf_tz.vfd_providers.utils import get_vat_amount
from csf_tz.vfd_support import utils as vfd_utils

VFDPLUS_REQUEST = "csf_tz.vfd_providers.doctype.vfdplus_settings.vfdplus_settings.requests.request"
VFDPLUS_SLEEP = "csf_tz.vfd_providers.doctype.vfdplus_settings.vfdplus_settings.sleep"
TOTAL_REQUEST = "csf_tz.vfd_providers.doctype.total_vfd_setting.total_vfd_setting.requests.request"
TOTAL_SLEEP = "csf_tz.vfd_providers.doctype.total_vfd_setting.total_vfd_setting.sleep"
SIMPLIFY_REQUEST = "csf_tz.vfd_providers.doctype.simplify_vfd_settings.simplify_vfd_settings.requests.request"
SIMPLIFY_SLEEP = "csf_tz.vfd_providers.doctype.simplify_vfd_settings.simplify_vfd_settings.sleep"

PLUS_RECEIPT = {
	"msg_status": "OK",
	"msg_code": 2000,
	"msg_data": {"rctvnum": "ABC123", "idate": "2026-08-25", "itime": "10:20:30"},
}
TOTAL_RECEIPT = {
	"status": 200,
	"rctvnum": "778899",
	"verificationLink": "https://verify.tra.go.tz/778899_102030",
	"localDate": "2026-08-25",
	"localTime": "10:20:30",
}
SIMPLIFY_RECEIPT = {
	"success": True,
	"issuedAt": "2026-08-25 10:20:30",
	"verificationUrl": "https://verify.tra.go.tz/SIM123_102030",
	"verificationCode": "SIM123",
	"invoiceId": "inv-1",
}


def posting_doc(invoice):
	invoice.reload()
	return frappe.get_doc("VFD Provider Posting", invoice.vfd_posting_info)


def set_setting(doctype, fieldname, value):
	frappe.db.set_value(doctype, COMPANY, fieldname, value)
	frappe.clear_document_cache(doctype, COMPANY)


class TestGetVatAmount(UnitTestCase):
	def test_exclusive_standard_rate_adds_vat(self):
		item = frappe._dict(base_net_amount=100, base_amount=100)
		self.assertEqual(get_vat_amount(item, "A", precision=2), 118.0)
		self.assertEqual(get_vat_amount(item, "1"), 118.0)

	def test_inclusive_and_non_standard_use_base_amount(self):
		inclusive = frappe._dict(base_net_amount=84.75, base_amount=100)
		self.assertEqual(get_vat_amount(inclusive, "A", precision=2), 100)
		self.assertEqual(get_vat_amount(inclusive, "A"), 100)
		exempt = frappe._dict(base_net_amount=100, base_amount=100)
		self.assertEqual(get_vat_amount(exempt, "E", precision=2), 100)
		self.assertEqual(get_vat_amount(exempt, "E"), 100)

	def test_distributed_discount_counts_as_exclusive(self):
		item = frappe._dict(base_net_amount=90, base_amount=100, distributed_discount_amount=10)
		self.assertEqual(get_vat_amount(item, "A", precision=2), 118.0)


class TestVFDPlusProvider(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_vfd_records()
		set_company_provider("VFDPlus")

	def test_settings_validate_loads_serial_info(self):
		settings = frappe.get_doc("VFDPlus Settings", COMPANY)
		self.assertEqual(settings.serial_id, "SER-1")
		self.assertEqual(settings.serial_code, "CRED-1")
		self.assertEqual(settings.vat_enabled, 1)
		self.assertIn("SER-1", settings.response)
		body = dict(SERIAL_INFO, msg_data=dict(SERIAL_INFO["msg_data"], tin="555"))
		with patch(VFDPLUS_REQUEST, return_value=fake_response(body)) as request:
			settings.save()
		self.assertEqual(settings.tin, "555")
		self.assertIn("555", settings.response)
		kwargs = request.call_args.kwargs
		self.assertEqual(kwargs["method"], "GET")
		self.assertEqual(kwargs["url"], "https://vfdplus.test/api/serial")
		self.assertEqual(kwargs["headers"]["VFDPLUS-API-KEY"], "plus-key")

	def test_get_serial_info_saves_outside_validate(self):
		settings = frappe.get_doc("VFDPlus Settings", COMPANY)
		body = dict(SERIAL_INFO, msg_data=dict(SERIAL_INFO["msg_data"], vrn="VRN-9"))
		with patch(VFDPLUS_REQUEST, return_value=fake_response(body)):
			vfdplus.get_serial_info(settings, method="on_update")
		self.assertEqual(frappe.db.get_value("VFDPlus Settings", COMPANY, "vrn"), "VRN-9")

	def test_get_account_info(self):
		body = {"msg_status": "OK", "msg_code": 2000, "msg_data": {"account_id": "acc-1"}}
		with patch(VFDPLUS_REQUEST, return_value=fake_response(body)) as request:
			self.assertEqual(vfdplus.get_account_info(COMPANY), body)
		self.assertEqual(request.call_args.kwargs["url"], "https://vfdplus.test/api/account")

	def test_get_payload(self):
		invoice = make_sales_invoice(submit=True)
		payload = vfdplus.get_payload(invoice)
		self.assertEqual(payload["credential_code"], "CRED-1")
		self.assertEqual(payload["trans_no"], invoice.name)
		self.assertEqual(payload["customer_info"]["cust_id"], "123456789")
		self.assertEqual(payload["customer_info"]["cust_id_type"], "1- TIN")
		self.assertEqual(payload["payment_methods"], [{"pmt_type": "INVOICE", "pmt_amount": 236.0}])
		self.assertEqual(payload["cart_totals"]["total_amount"], 236.0)
		self.assertEqual(payload["cart_totals"]["item_counts"], 1)
		item = payload["cart_items"][0]
		self.assertEqual(item["vat_rate_code"], "A")
		self.assertEqual(item["vat_rate_id"], "1")
		self.assertEqual(item["item_qty"], 2)
		self.assertEqual(item["sp"], 236.0)
		self.assertEqual(item["usp"], 118.0)
		self.assertEqual(payload["user_info"]["username"], "Administrator")

	def test_get_payload_exempt_item(self):
		invoice = make_sales_invoice(item_tax_template=EXEMPT_TEMPLATE, submit=True)
		payload = vfdplus.get_payload(invoice)
		self.assertEqual(payload["cart_items"][0]["vat_rate_code"], "E")
		self.assertEqual(payload["cart_items"][0]["sp"], 200.0)

	def test_autogenerate_on_submit_posts_receipt(self):
		with patch(VFDPLUS_REQUEST, return_value=fake_response(PLUS_RECEIPT)) as request:
			invoice = make_sales_invoice(is_auto_generate_vfd=1, submit=True)
		request.assert_called_once()
		kwargs = request.call_args.kwargs
		self.assertEqual(kwargs["method"], "POST")
		self.assertEqual(kwargs["url"], "https://vfdplus.test/api/receipt")
		self.assertEqual(json.loads(kwargs["data"])["trans_no"], invoice.name)

		invoice.reload()
		self.assertEqual(invoice.vfd_status, "Success")
		self.assertEqual(invoice.vfd_rctvnum, "ABC123")
		self.assertEqual(invoice.vfd_verification_url, "https://verify.tra.go.tz/ABC123_102030")
		self.assertEqual(str(invoice.vfd_date), "2026-08-25")
		self.assertEqual(str(invoice.vfd_time), "10:20:30")

		posting = posting_doc(invoice)
		self.assertEqual(posting.sales_invoice, invoice.name)
		self.assertEqual(posting.ackcode, 2000)
		self.assertIn("ABC123", posting.ackmsg)
		self.assertIn(invoice.name, posting.req_data)
		self.assertIn("plus-key", posting.req_headers)

	def test_generate_tra_vfd_post_updates_database(self):
		invoice = make_sales_invoice(submit=True)
		self.assertEqual(invoice.vfd_status, "Not Sent")
		with (
			patch(VFDPLUS_REQUEST, return_value=fake_response(PLUS_RECEIPT)),
			patch.object(frappe.db, "commit"),
		):
			result = vfd_utils.generate_tra_vfd(invoice.name)
		self.assertEqual(result["vfd_provider"], "VFDPlus")
		self.assertFalse(result["preview"])
		invoice.reload()
		self.assertEqual(invoice.vfd_status, "Success")
		self.assertEqual(invoice.vfd_rctvnum, "ABC123")
		self.assertEqual(posting_doc(invoice).ackcode, 2000)

	def test_generate_tra_vfd_preview_returns_payload(self):
		set_setting("VFDPlus Settings", "enable_vfd_preview", 1)
		self.addCleanup(set_setting, "VFDPlus Settings", "enable_vfd_preview", 0)
		invoice = make_sales_invoice(submit=True)
		with patch(VFDPLUS_REQUEST) as request:
			result = vfd_utils.generate_tra_vfd(invoice.name)
		request.assert_not_called()
		self.assertTrue(result["preview"])
		self.assertEqual(result["data"]["trans_no"], invoice.name)
		with (
			patch(VFDPLUS_REQUEST, return_value=fake_response(PLUS_RECEIPT)),
			patch.object(frappe.db, "commit"),
		):
			result = vfd_utils.generate_tra_vfd(invoice.name, caller="Scheduler")
		self.assertFalse(result["preview"])

	def test_generate_tra_vfd_skips_non_vfd_invoices(self):
		invoice = make_sales_invoice(
			is_not_vfd_invoice=1, item_tax_template=None, with_taxes=False, submit=True
		)
		self.assertIsNone(vfd_utils.generate_tra_vfd(invoice.name))
		invoice = make_sales_invoice(submit=True)
		invoice.db_set("vfd_status", "Success")
		self.assertIsNone(vfd_utils.generate_tra_vfd(invoice.name))

	def test_generate_tra_vfd_checks_start_date(self):
		invoice = make_sales_invoice(submit=True)
		set_setting("VFDPlus Settings", "vfd_start_date", None)
		self.addCleanup(set_setting, "VFDPlus Settings", "vfd_start_date", add_days(nowdate(), -30))
		self.assertRaisesRegex(
			frappe.ValidationError, "VFD Start Date", vfd_utils.generate_tra_vfd, invoice.name
		)
		set_setting("VFDPlus Settings", "vfd_start_date", add_days(nowdate(), 1))
		self.assertRaisesRegex(
			frappe.ValidationError, "cannot be generated", vfd_utils.generate_tra_vfd, invoice.name
		)

	def test_unsupported_provider_throws(self):
		# Dispatch keys on the settings doctype, so a provider is unsupported when
		# no handler owns that doctype. The record name is free to be anything.
		frappe.get_doc(
			{
				"doctype": "VFD Provider",
				"vfd_provider": "OtherVFD",
				"vfd_provider_settings": "ToDo",
			}
		).insert()
		set_company_provider("OtherVFD")
		self.addCleanup(set_company_provider, "VFDPlus")
		invoice = make_sales_invoice(submit=True)
		self.assertRaisesRegex(
			frappe.ValidationError, "not supported", vfd_utils.generate_tra_vfd, invoice.name
		)
		set_setting("VFDPlus Settings", "enable_vfd_preview", 1)
		self.addCleanup(set_setting, "VFDPlus Settings", "enable_vfd_preview", 0)
		self.assertRaisesRegex(
			frappe.ValidationError, "not supported", vfd_utils.generate_tra_vfd, invoice.name
		)

	def test_api_error_status_throws_after_retries(self):
		invoice = make_sales_invoice(submit=True)
		body = {"msg_status": "ERROR", "msg_code": 4001, "msg_data": {}}
		with (
			patch(VFDPLUS_REQUEST, return_value=fake_response(body)) as request,
			patch(VFDPLUS_SLEEP),
			patch.object(frappe, "log_error") as log_error,
		):
			self.assertRaisesRegex(
				frappe.ValidationError, "Connection failure", vfdplus.post_fiscal_receipt, invoice
			)
		self.assertEqual(request.call_count, 3)
		self.assertIn("Error returned from VFDPlus: 4001", log_error.call_args.kwargs["message"])
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "vfd_status"), "Not Sent")

	def test_http_error_throws(self):
		invoice = make_sales_invoice(submit=True)
		response = fake_response({"detail": "bad"}, status_code=500, ok=False)
		with patch(VFDPLUS_REQUEST, return_value=response), patch(VFDPLUS_SLEEP):
			self.assertRaisesRegex(
				frappe.ValidationError,
				"Connection failure",
				vfdplus.post_fiscal_receipt,
				invoice_id=invoice.name,
			)

	def test_warning_already_posted_is_accepted(self):
		invoice = make_sales_invoice(submit=True)
		body = dict(PLUS_RECEIPT, msg_status="WARNING", msg_code=4015)
		with patch(VFDPLUS_REQUEST, return_value=fake_response(body)), patch.object(frappe.db, "commit"):
			result = vfdplus.post_fiscal_receipt(invoice_id=invoice.name, method="POST")
		self.assertEqual(result["data"]["msg_code"], 4015)
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "vfd_rctvnum"), "ABC123")

	def test_post_fiscal_receipt_requires_invoice(self):
		self.assertRaisesRegex(
			frappe.ValidationError, "Sales Invoice is required", vfdplus.post_fiscal_receipt
		)
		self.assertRaisesRegex(
			frappe.ValidationError, "Sales Invoice is required", total_vfd.post_fiscal_receipt
		)
		self.assertRaisesRegex(
			frappe.ValidationError, "Sales Invoice is required", simplify.post_fiscal_receipt
		)


class TestTotalVFDProvider(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_vfd_records()
		set_company_provider("TotalVFD")

	def test_get_payload(self):
		invoice = make_sales_invoice(
			items=[
				{"item_code": ITEM, "qty": 2, "rate": 100},
				{"item_code": SECOND_ITEM, "qty": 1, "rate": 50},
			],
			submit=True,
		)
		payload = total_vfd.get_payload(invoice)
		self.assertEqual(payload["serial"], "TOTAL-SERIAL")
		self.assertEqual(payload["referenceNumber"], invoice.name)
		self.assertEqual(payload["customer"]["idType"], "1")
		self.assertEqual(payload["customer"]["idValue"], "123456789")
		self.assertEqual(payload["payments"], [{"type": "invoice", "amount": 295.0}])
		self.assertEqual(len(payload["items"]), 2)
		self.assertEqual(payload["items"][0]["price"], 236.0)
		self.assertEqual(payload["items"][0]["vatGroup"], "A")
		self.assertEqual(payload["items"][1]["price"], 59.0)

	def test_get_payload_grouped_by_vat(self):
		set_setting("Total VFD Setting", "is_vat_grouped", 1)
		self.addCleanup(set_setting, "Total VFD Setting", "is_vat_grouped", 0)
		invoice = make_sales_invoice(
			items=[
				{"item_code": ITEM, "qty": 2, "rate": 100},
				{"item_code": SECOND_ITEM, "qty": 1, "rate": 50},
			],
			submit=True,
		)
		payload = total_vfd.get_payload(invoice)
		self.assertEqual(len(payload["items"]), 1)
		self.assertEqual(payload["items"][0]["id"], "Items in VAT Group A")
		self.assertEqual(payload["items"][0]["price"], 295.0)
		self.assertEqual(payload["items"][0]["qty"], 1)

	def test_autogenerate_on_submit_posts_receipt(self):
		with patch(TOTAL_REQUEST, return_value=fake_response(TOTAL_RECEIPT)) as request:
			invoice = make_sales_invoice(is_auto_generate_vfd=1, submit=True)
		kwargs = request.call_args.kwargs
		self.assertEqual(kwargs["url"], "https://totalvfd.test/sales")
		self.assertEqual(kwargs["headers"]["Authorization"], "Bearer total-token")
		self.assertEqual(kwargs["headers"]["x-active-business"], "business-1")
		self.assertEqual(json.loads(kwargs["data"])["referenceNumber"], invoice.name)

		invoice.reload()
		self.assertEqual(invoice.vfd_status, "Success")
		self.assertEqual(invoice.vfd_rctvnum, "778899")
		self.assertEqual(invoice.vfd_verification_url, TOTAL_RECEIPT["verificationLink"])
		self.assertEqual(str(invoice.vfd_date), "2026-08-25")
		posting = posting_doc(invoice)
		self.assertEqual(posting.ackcode, 200)
		self.assertEqual(posting.sales_invoice, invoice.name)
		self.assertIn("778899", posting.ackmsg)
		self.assertIn("total-token", posting.req_headers)

	def test_generate_tra_vfd_post_updates_database(self):
		invoice = make_sales_invoice(submit=True)
		with (
			patch(TOTAL_REQUEST, return_value=fake_response(TOTAL_RECEIPT)),
			patch.object(frappe.db, "commit"),
		):
			result = vfd_utils.generate_tra_vfd(invoice.name)
		self.assertEqual(result["vfd_provider"], "TotalVFD")
		invoice.reload()
		self.assertEqual(invoice.vfd_status, "Success")
		self.assertEqual(invoice.vfd_rctvnum, "778899")
		self.assertEqual(posting_doc(invoice).ackcode, 200)

	def test_conflict_response_uses_data_key(self):
		invoice = make_sales_invoice(submit=True)
		response = fake_response({"data": TOTAL_RECEIPT}, status_code=409, ok=False)
		with patch(TOTAL_REQUEST, return_value=response), patch.object(frappe.db, "commit"):
			result = total_vfd.post_fiscal_receipt(invoice_id=invoice.name)
		self.assertEqual(result["data"]["rctvnum"], "778899")

	def test_http_error_throws_after_retries(self):
		invoice = make_sales_invoice(submit=True)
		response = fake_response({"error": "down"}, status_code=500, ok=False)
		with patch(TOTAL_REQUEST, return_value=response) as request, patch(TOTAL_SLEEP):
			self.assertRaisesRegex(
				frappe.ValidationError, "Connection failure", total_vfd.post_fiscal_receipt, invoice
			)
		self.assertEqual(request.call_count, 3)


class TestSimplifyVFDProvider(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_vfd_records()
		set_company_provider("SimplifyVFD")

	def settings(self):
		frappe.clear_document_cache("Simplify VFD Settings", COMPANY)
		return frappe.get_doc("Simplify VFD Settings", COMPANY)

	def test_get_bearer_token(self):
		settings = self.settings()
		body = {"token": "fresh-token", "refresh_token": "fresh-refresh"}
		with patch(SIMPLIFY_REQUEST, return_value=fake_response(body)) as request:
			self.assertTrue(settings.get_bearer_token())
		kwargs = request.call_args.kwargs
		self.assertEqual(kwargs["url"], "https://simplify.test/login")
		self.assertEqual(
			json.loads(kwargs["data"]), {"username": "simplify-user", "password": "simplify-pass"}
		)
		self.assertNotIn("Authorization", kwargs["headers"])
		self.assertEqual(settings.get_password("bearer_token"), "fresh-token")
		self.assertEqual(settings.get_password("refresh_token"), "fresh-refresh")
		self.assertGreater(get_datetime(settings.token_expires), now_datetime())

	def test_get_bearer_token_rejects_bad_credentials(self):
		settings = self.settings()
		with patch(SIMPLIFY_REQUEST, return_value=fake_response({"message": "denied"})):
			self.assertRaisesRegex(frappe.ValidationError, "Invalid username", settings.get_bearer_token)
		settings.username = ""
		self.assertRaisesRegex(frappe.ValidationError, "Username and Password", settings.get_bearer_token)

	def test_refresh_bearer_token(self):
		settings = self.settings()
		stored_refresh_token = settings.get_password("refresh_token")
		body = {"token": "refreshed", "refresh_token": "refreshed-r"}
		with patch(SIMPLIFY_REQUEST, return_value=fake_response(body)) as request:
			self.assertTrue(settings.refresh_bearer_token())
		self.assertEqual(request.call_args.kwargs["url"], "https://simplify.test/refresh")
		self.assertEqual(
			json.loads(request.call_args.kwargs["data"]), {"refresh_token": stored_refresh_token}
		)
		self.assertEqual(settings.get_password("bearer_token"), "refreshed")
		with patch(SIMPLIFY_REQUEST, return_value=fake_response({"token": "x"})):
			self.assertRaisesRegex(
				frappe.ValidationError, "Invalid refresh token", settings.refresh_bearer_token
			)

	def test_refresh_requires_stored_refresh_token(self):
		settings = self.settings()
		settings.refresh_token = None
		self.assertRaisesRegex(
			frappe.ValidationError, "Refresh Token is not found", settings.refresh_bearer_token
		)

	def test_get_access_token_refreshes_expired_tokens(self):
		set_setting("Simplify VFD Settings", "token_expires", add_to_date(now_datetime(), minutes=-1))
		body = {"token": "sched-token", "refresh_token": "sched-refresh"}
		with patch(SIMPLIFY_REQUEST, return_value=fake_response(body)) as request:
			simplify.get_access_token()
		self.assertEqual(request.call_args.kwargs["url"], "https://simplify.test/refresh")
		self.assertEqual(self.settings().get_password("bearer_token"), "sched-token")
		with patch(SIMPLIFY_REQUEST) as request:
			simplify.get_access_token()
		request.assert_not_called()

	def test_get_refresh_token_logs_in_again(self):
		body = {"token": "login-token", "refresh_token": "login-refresh"}
		with patch(SIMPLIFY_REQUEST, return_value=fake_response(body)) as request:
			simplify.get_refresh_token()
		self.assertEqual(request.call_args.kwargs["url"], "https://simplify.test/login")
		self.assertEqual(self.settings().get_password("refresh_token"), "login-refresh")

	def test_get_payload(self):
		invoice = make_sales_invoice(submit=True)
		payload = simplify.get_payload(invoice)
		self.assertEqual(payload["partnerInvoiceId"], invoice.name)
		self.assertEqual(payload["invoiceAmountType"], "INCLUSIVE")
		self.assertEqual(payload["customer"]["identificationType"], "TAX_IDENTIFICATION_NUMBER")
		self.assertEqual(payload["customer"]["identificationNumber"], "123456789")
		self.assertEqual(payload["customer"]["name"], invoice.customer_name)
		self.assertEqual(payload["payments"], [{"type": "INVOICE", "amount": 236.0}])
		item = payload["items"][0]
		self.assertEqual(item["description"], ITEM)
		self.assertEqual(item["quantity"], 2)
		self.assertEqual(item["unitAmount"], 118.0)
		self.assertEqual(item["taxType"], "STANDARD")

	def test_get_payload_without_customer_id(self):
		invoice = make_sales_invoice(submit=True)
		invoice.vfd_cust_id_type = "6- Other"
		invoice.vfd_cust_id = "999999999"
		payload = simplify.get_payload(invoice)
		self.assertEqual(payload["customer"]["identificationType"], "NO_IDENTIFICATION")
		self.assertEqual(payload["customer"]["identificationNumber"], "")

	def test_autogenerate_on_submit_posts_receipt(self):
		with patch(SIMPLIFY_REQUEST, return_value=fake_response(SIMPLIFY_RECEIPT)) as request:
			invoice = make_sales_invoice(is_auto_generate_vfd=1, submit=True)
		kwargs = request.call_args.kwargs
		self.assertEqual(kwargs["url"], "https://simplify.test/invoice")
		self.assertEqual(kwargs["headers"]["Authorization"], "Bearer simplify-token")
		self.assertEqual(json.loads(kwargs["data"])["partnerInvoiceId"], invoice.name)

		invoice.reload()
		self.assertEqual(invoice.vfd_status, "Success")
		self.assertEqual(invoice.vfd_rctvnum, "SIM123")
		self.assertEqual(invoice.vfd_verification_url, SIMPLIFY_RECEIPT["verificationUrl"])
		self.assertEqual(str(invoice.vfd_date), "2026-08-25")
		self.assertEqual(str(invoice.vfd_time), "10:20:30")
		posting = posting_doc(invoice)
		self.assertEqual(posting.ackcode, 200)
		self.assertIn("SIM123", posting.ackmsg)
		self.assertIn(invoice.name, posting.req_data)
		self.assertTrue(
			frappe.db.exists("Comment", {"reference_name": invoice.name, "content": "VFD Invoice ID: inv-1"})
		)

	def test_failed_response_marks_invoice_failed(self):
		body = {"success": False, "message": "rejected"}
		with patch(SIMPLIFY_REQUEST, return_value=fake_response(body)):
			invoice = make_sales_invoice(is_auto_generate_vfd=1, submit=True)
		invoice.reload()
		self.assertEqual(invoice.vfd_status, "Failed")
		self.assertFalse(invoice.vfd_rctvnum)
		self.assertEqual(str(posting_doc(invoice).date), nowdate())

	def test_generate_tra_vfd_post_updates_database(self):
		invoice = make_sales_invoice(submit=True)
		with (
			patch(SIMPLIFY_REQUEST, return_value=fake_response(SIMPLIFY_RECEIPT)),
			patch.object(frappe.db, "commit"),
		):
			result = vfd_utils.generate_tra_vfd(invoice.name)
		self.assertEqual(result["vfd_provider"], "SimplifyVFD")
		invoice.reload()
		self.assertEqual(invoice.vfd_status, "Success")
		self.assertEqual(invoice.vfd_rctvnum, "SIM123")

	def test_expired_token_is_refreshed_before_posting(self):
		set_setting("Simplify VFD Settings", "token_expires", add_to_date(now_datetime(), minutes=-1))
		invoice = make_sales_invoice(submit=True)
		responses = [
			fake_response({"token": "renewed", "refresh_token": "renewed-r"}),
			fake_response(SIMPLIFY_RECEIPT),
		]
		with patch(SIMPLIFY_REQUEST, side_effect=responses) as request, patch.object(frappe.db, "commit"):
			simplify.post_fiscal_receipt(invoice_id=invoice.name)
		self.assertEqual(request.call_count, 2)
		self.assertEqual(request.call_args_list[0].kwargs["url"], "https://simplify.test/refresh")
		self.assertEqual(request.call_args_list[1].kwargs["headers"]["Authorization"], "Bearer renewed")

	def test_http_error_throws_after_retries(self):
		invoice = make_sales_invoice(submit=True)
		response = fake_response({"error": "down"}, status_code=500, ok=False)
		with patch(SIMPLIFY_REQUEST, return_value=response) as request, patch(SIMPLIFY_SLEEP):
			self.assertRaisesRegex(frappe.ValidationError, "Error is", simplify.post_fiscal_receipt, invoice)
		self.assertEqual(request.call_count, 3)


class TestPostingAllVFDInvoices(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_vfd_records()
		set_company_provider("VFDPlus")

	def tearDown(self):
		frappe.local.flags.vfd_posting = False

	def test_posts_pending_invoices(self):
		invoice = make_sales_invoice(submit=True)
		invoice.db_set("vfd_status", "Pending")
		with (
			patch(VFDPLUS_REQUEST, return_value=fake_response(PLUS_RECEIPT)) as request,
			patch.object(frappe.db, "commit"),
		):
			vfd_utils.posting_all_vfd_invoices()
		self.assertEqual(json.loads(request.call_args.kwargs["data"])["trans_no"], invoice.name)
		invoice.reload()
		self.assertEqual(invoice.vfd_status, "Success")
		self.assertEqual(invoice.vfd_rctvnum, "ABC123")
		self.assertFalse(frappe.local.flags.vfd_posting)

	def test_skips_sent_and_non_vfd_invoices(self):
		make_sales_invoice(submit=True)
		with patch(VFDPLUS_REQUEST) as request:
			vfd_utils.posting_all_vfd_invoices()
		request.assert_not_called()

	def test_flag_guard_prevents_parallel_runs(self):
		frappe.local.flags.vfd_posting = True
		with patch(VFDPLUS_REQUEST) as request, patch.object(frappe, "log_error") as log_error:
			vfd_utils.posting_all_vfd_invoices()
		request.assert_not_called()
		log_error.assert_called_once()

	def test_posts_with_other_providers(self):
		for provider, request_path, body in (
			("TotalVFD", TOTAL_REQUEST, TOTAL_RECEIPT),
			("SimplifyVFD", SIMPLIFY_REQUEST, SIMPLIFY_RECEIPT),
		):
			set_company_provider(provider)
			self.addCleanup(set_company_provider, "VFDPlus")
			invoice = make_sales_invoice(submit=True)
			invoice.db_set("vfd_status", "Failed")
			with patch(request_path, return_value=fake_response(body)), patch.object(frappe.db, "commit"):
				vfd_utils.posting_all_vfd_invoices()
			self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "vfd_status"), "Success")

	def test_provider_records(self):
		for name, info in PROVIDERS.items():
			provider = frappe.get_doc("VFD Provider", name)
			self.assertEqual(provider.vfd_provider_settings, info["settings"])
			self.assertEqual({row.key: row.value for row in provider.attributes}, info["attributes"])


class TestCompanyWithoutVFDProvider(IntegrationTestCase):
	"""A company with no VFD Provider must opt out quietly, not raise."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_vfd_records()
		set_company_provider("VFDPlus")

	def drop_company_provider(self):
		frappe.delete_doc("Company VFD Provider", COMPANY, force=True, ignore_permissions=True)
		frappe.clear_document_cache("Company VFD Provider", COMPANY)
		self.addCleanup(set_company_provider, "VFDPlus")

	def test_missing_company_vfd_provider_returns_none(self):
		self.drop_company_provider()

		self.assertIsNone(vfd_utils.get_company_vfd_provider(COMPANY))

	def test_blank_provider_link_returns_none(self):
		doc = set_company_provider("VFDPlus")
		self.addCleanup(set_company_provider, "VFDPlus")
		frappe.db.set_value("Company VFD Provider", doc.name, "vfd_provider", None)
		frappe.clear_document_cache("Company VFD Provider", doc.name)

		self.assertIsNone(vfd_utils.get_company_vfd_provider(COMPANY))

	def test_submit_succeeds_and_posts_nothing_without_a_provider(self):
		self.drop_company_provider()

		with patch(VFDPLUS_REQUEST) as request:
			invoice = make_sales_invoice(is_auto_generate_vfd=1, submit=True)

		request.assert_not_called()
		self.assertEqual(invoice.docstatus, 1)
		self.assertEqual(invoice.vfd_status, "Not Sent")

	def test_generate_tra_vfd_returns_none_without_a_provider(self):
		invoice = make_sales_invoice(submit=True)
		self.drop_company_provider()

		with patch(VFDPLUS_REQUEST) as request:
			self.assertIsNone(vfd_utils.generate_tra_vfd(invoice.name))

		request.assert_not_called()
