"""Compatibility endpoints for callers using the old CSF TZ OTP paths."""

import frappe
from av_tools.authotp.doctype.otp_register import otp_register as canonical


@frappe.whitelist()
def register_otp(otp_doc):
    return canonical.register_otp(otp_doc)


@frappe.whitelist()
def validate_otp(otp_doc, otp_code, submit=False):
    return canonical.validate_otp(otp_doc, otp_code, submit=submit)


@frappe.whitelist()
def validate_doc_otp(otp_register_name, otp_code):
    return canonical.validate_doc_otp(otp_register_name, otp_code)


def register_otp_app(otp_doc):
    return canonical.register_otp_app(otp_doc)


def register_otp_sms(otp_doc=None):
    return canonical.register_otp_sms(otp_doc)


def register_otp_email(otp_doc=None):
    return canonical.register_otp_email(otp_doc)
