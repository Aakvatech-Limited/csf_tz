# Copyright (c) 2026, Aakvatech and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.monkey_patches import airtel_sms

GATEWAY_URL = "https://www.airtel.co.tz/gateway/v1/sendDefaultSms"


def make_settings():
    return frappe._dict(
        sms_gateway_url=GATEWAY_URL,
        message_parameter="message",
        receiver_parameter="destinationAddress",
        parameters=[
            frappe._dict(parameter="Authorization", value="Basic token", header=1),
            frappe._dict(parameter="Content-Type", value="application/json", header=1),
            frappe._dict(parameter="customerId", value="cust-1", header=0),
            frappe._dict(parameter="senderId", value="SHREEHARI", header=0),
            frappe._dict(parameter="subAccountId", value="sub-1", header=0),
        ],
    )


def make_response(ok=True, status_code=200, text="{}", payload=None):
    response = frappe._dict(ok=ok, status_code=status_code, text=text)
    response.json = lambda: payload if payload is not None else {}
    return response


class TestAirtelPatchIsInstalled(FrappeTestCase):
    def test_importing_the_module_replaces_the_frappe_gateway_call(self):
        self.assertIs(airtel_sms.sms_settings.send_via_gateway, airtel_sms.send_via_gateway)

    def test_keeps_a_reference_to_the_frappe_implementation_to_fall_back_on(self):
        self.assertEqual(
            airtel_sms.standard_send_via_gateway.__module__,
            "frappe.core.doctype.sms_settings.sms_settings",
        )


class TestAirtelNumber(FrappeTestCase):
    def test_accepts_the_formats_contacts_are_stored_in(self):
        for number in ["+255675353248", "255675353248", "0675353248", "675353248"]:
            with self.subTest(number=number):
                self.assertEqual(airtel_sms.get_airtel_number(number), "255675353248")

    def test_strips_separators_and_international_prefix(self):
        self.assertEqual(airtel_sms.get_airtel_number("+255 675-353 248"), "255675353248")
        self.assertEqual(airtel_sms.get_airtel_number("00255675353248"), "255675353248")

    def test_strips_a_trunk_zero_left_after_the_country_code(self):
        self.assertEqual(airtel_sms.get_airtel_number("+255 0675 353 248"), "255675353248")

    def test_rejects_a_number_of_the_wrong_length(self):
        for number in ["25567535324", "2556753532489", "0675"]:
            with self.subTest(number=number):
                self.assertIsNone(airtel_sms.get_airtel_number(number))

    def test_drops_invalid_numbers_and_keeps_the_rest(self):
        numbers = ["0675353248", "0675", "255700000001"]

        self.assertEqual(airtel_sms.get_airtel_numbers(numbers), ["255675353248", "255700000001"])


class TestAirtelPayload(FrappeTestCase):
    def test_sends_recipients_as_an_array_under_the_receiver_parameter(self):
        payload = airtel_sms.build_payload(make_settings(), ["255675353248", "255700000001"], "Hello")

        self.assertEqual(payload["destinationAddress"], ["255675353248", "255700000001"])
        self.assertEqual(payload["message"], "Hello")

    def test_nests_the_sub_account_id_under_meta_data(self):
        payload = airtel_sms.build_payload(make_settings(), ["255675353248"], "Hello")

        self.assertEqual(payload["metaData"], {"subAccountId": "sub-1"})
        self.assertNotIn("subAccountId", payload)

    def test_keeps_body_parameters_and_drops_header_parameters(self):
        payload = airtel_sms.build_payload(make_settings(), ["255675353248"], "Hello")

        self.assertEqual(payload["customerId"], "cust-1")
        self.assertEqual(payload["senderId"], "SHREEHARI")
        self.assertNotIn("Authorization", payload)

    def test_omits_meta_data_when_no_sub_account_is_configured(self):
        settings = make_settings()
        settings.parameters = [row for row in settings.parameters if row.parameter != "subAccountId"]

        self.assertNotIn("metaData", airtel_sms.build_payload(settings, ["255675353248"], "Hi"))


class TestSendViaGateway(FrappeTestCase):
    def setUp(self):
        self.arg = {
            "receiver_list": ["+255675353248", "0700000001"],
            "message": b"Hello",
            "success_msg": False,
        }

    def send(self, enabled=True, response=None):
        with (
            patch.object(frappe.db, "get_single_value", return_value=enabled),
            patch.object(frappe, "get_cached_doc", return_value=make_settings()),
            patch.object(frappe, "log_error"),
            patch.object(airtel_sms.sms_settings, "create_sms_log"),
            patch.object(airtel_sms.requests, "post", return_value=response or make_response()) as post,
        ):
            airtel_sms.send_via_gateway(self.arg)
        return post

    def test_falls_back_to_the_standard_request_when_the_checkbox_is_off(self):
        with (
            patch.object(frappe.db, "get_single_value", return_value=0),
            patch.object(airtel_sms, "standard_send_via_gateway") as standard,
        ):
            airtel_sms.send_via_gateway(self.arg)

        standard.assert_called_once_with(self.arg)

    def test_sends_every_recipient_in_a_single_request(self):
        post = self.send()

        self.assertEqual(post.call_count, 1)
        self.assertEqual(
            post.call_args.kwargs["json"]["destinationAddress"],
            ["255675353248", "255700000001"],
        )

    def test_sends_the_configured_headers_to_the_gateway_url(self):
        post = self.send()

        self.assertEqual(post.call_args.args[0], GATEWAY_URL)
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Basic token")

    def test_always_sets_a_timeout(self):
        self.assertEqual(self.send().call_args.kwargs["timeout"], airtel_sms.REQUEST_TIMEOUT)

    def test_reports_the_reason_airtel_rejected_the_message(self):
        rejection = make_response(
            ok=False,
            status_code=400,
            text='{"errorCode":"INVALID_HEADER_ID"}',
            payload={"errorCode": "INVALID_HEADER_ID", "errorMessage": "Empty headerId"},
        )

        with self.assertRaises(frappe.ValidationError) as raised:
            self.send(response=rejection)

        self.assertIn("Empty headerId", str(raised.exception))

    def test_still_reports_the_status_when_the_gateway_body_is_empty(self):
        # a content type the gateway will not accept comes back 406 with no body
        with self.assertRaises(frappe.ValidationError) as raised:
            self.send(response=make_response(ok=False, status_code=406, text=""))

        self.assertIn("406", str(raised.exception))

    def test_sends_to_the_good_numbers_when_one_recipient_is_malformed(self):
        self.arg["receiver_list"] = ["0675353248", "not-a-number", "255700000001"]

        post = self.send()

        self.assertEqual(
            post.call_args.kwargs["json"]["destinationAddress"],
            ["255675353248", "255700000001"],
        )

    def test_refuses_to_call_the_gateway_when_no_number_survives(self):
        self.arg["receiver_list"] = ["0675", "not-a-number"]

        with (
            patch.object(frappe.db, "get_single_value", return_value=1),
            patch.object(airtel_sms.requests, "post") as post,
        ):
            self.assertRaises(frappe.ValidationError, airtel_sms.send_via_gateway, self.arg)

        post.assert_not_called()

    def test_logs_an_sms_log_entry_only_after_the_gateway_accepts(self):
        with (
            patch.object(frappe.db, "get_single_value", return_value=1),
            patch.object(frappe, "get_cached_doc", return_value=make_settings()),
            patch.object(frappe, "log_error"),
            patch.object(airtel_sms.sms_settings, "create_sms_log") as create_sms_log,
            patch.object(
                airtel_sms.requests,
                "post",
                return_value=make_response(ok=False, status_code=400, text="{}"),
            ),
        ):
            self.assertRaises(frappe.ValidationError, airtel_sms.send_via_gateway, self.arg)

        create_sms_log.assert_not_called()
