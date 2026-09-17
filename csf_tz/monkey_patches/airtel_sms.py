import re

import frappe
import requests
from frappe import _
from frappe.core.doctype.sms_settings import sms_settings

SUB_ACCOUNT_PARAMETER = "subAccountId"
COUNTRY_CODE = "255"
NATIONAL_NUMBER_LENGTH = 9
REQUEST_TIMEOUT = (5, 60)

standard_send_via_gateway = sms_settings.send_via_gateway


def send_via_gateway(arg):
    """Send through Airtel IQ when CSF TZ Settings asks for it, else use the standard request.

    Airtel wants every recipient in one JSON array and the sub account id nested under
    metaData. SMS Settings can only build flat string parameters, so it cannot express
    either and sends one request per recipient.
    """
    if not frappe.db.get_single_value("CSF TZ Settings", "enable_airtel_sms"):
        standard_send_via_gateway(arg)
        return

    receiver_list = get_airtel_numbers(arg.get("receiver_list"))
    if not receiver_list:
        frappe.throw(_("No valid Tanzanian mobile number to send to"), title=_("SMS Not Sent"))

    settings = frappe.get_cached_doc("SMS Settings", "SMS Settings")
    message = frappe.safe_decode(arg.get("message"))

    response = requests.post(
        settings.sms_gateway_url,
        json=build_payload(settings, receiver_list, message),
        headers=sms_settings.get_headers(settings),
        timeout=REQUEST_TIMEOUT,
    )
    if not response.ok:
        throw_gateway_error(response)

    sms_settings.create_sms_log(arg, receiver_list)
    if arg.get("success_msg"):
        frappe.msgprint(_("SMS sent successfully"))


def build_payload(settings, receiver_list, message):
    """Build the Airtel request from the SMS Settings parameters that are not headers."""
    payload = {row.parameter: row.value for row in settings.parameters if not row.header}

    sub_account_id = payload.pop(SUB_ACCOUNT_PARAMETER, None)
    if sub_account_id:
        payload["metaData"] = {SUB_ACCOUNT_PARAMETER: sub_account_id}

    payload[settings.receiver_parameter] = receiver_list
    payload[settings.message_parameter] = message
    return payload


def get_airtel_numbers(numbers):
    """Normalise recipients, dropping the ones Airtel would reject so the rest still go out."""
    normalised = [(number, get_airtel_number(number)) for number in numbers]

    skipped = [number for number, airtel_number in normalised if not airtel_number]
    if skipped:
        frappe.msgprint(_("Skipped invalid mobile numbers: {0}").format(", ".join(skipped)))

    return [airtel_number for _original, airtel_number in normalised if airtel_number]


def get_airtel_number(number):
    """Return a bare 255XXXXXXXXX number, or None when it is not a Tanzanian mobile number."""
    digits = re.sub(r"\D", "", number).lstrip("0")
    if digits.startswith(COUNTRY_CODE):
        digits = digits[len(COUNTRY_CODE) :]

    national_number = digits.lstrip("0")
    if len(national_number) != NATIONAL_NUMBER_LENGTH:
        return None

    return COUNTRY_CODE + national_number


def throw_gateway_error(response):
    body = response.text
    # throw rolls the transaction back, so the log has to outlive it
    frappe.log_error(
        title="Airtel SMS request failed",
        message=f"HTTP {response.status_code}\n{body}",
        defer_insert=True,
    )

    try:
        error = response.json()
        reason = error.get("errorMessage") or error.get("errorCode")
    except ValueError:
        reason = None

    # a rejected content type comes back empty, so the status carries the only clue
    frappe.throw(
        _("Airtel rejected the SMS (HTTP {0}): {1}").format(
            response.status_code, reason or body.strip() or _("no reason given")
        ),
        title=_("SMS Not Sent"),
    )


sms_settings.send_via_gateway = send_via_gateway
