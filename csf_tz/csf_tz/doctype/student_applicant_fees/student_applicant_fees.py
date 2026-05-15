# -*- coding: utf-8 -*-
# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import binascii
import os

import frappe
from frappe import _
from frappe.model.document import Document

from csf_tz.bank_api import cancel_invoice, invoice_submission


class StudentApplicantFees(Document):
	def after_insert(self):
		if not check_send_fee_details_to_bank(self.company):
			return
		callback_token = binascii.hexlify(os.urandom(14)).decode()
		self.db_set("callback_token", callback_token)
		series = frappe.get_value("Company", self.company, "nmb_series") or ""
		if not series:
			frappe.throw(_("Please set NMB User Series in Company {0}").format(self.company))
		reference = str(series) + "R" + str(self.name)
		if not self.abbr:
			self.db_set("abbr", frappe.get_value("Company", self.company, "abbr") or "")
		self.db_set("bank_reference", reference.replace("-", "").replace("RFEE" + self.abbr, ""))

	def on_submit(self):
		if not check_send_fee_details_to_bank(self.company):
			return
		invoice_submission(self)

	def on_cancel(self):
		if check_send_fee_details_to_bank(self.company):
			cancel_invoice(self, "on_cancel")
		doc = frappe.get_doc("Student Applicant", self.student)
		doc.bank_reference = None
		doc.student_applicant_fee = None
		doc.application_status = "Applied"
		doc.db_update()


def check_send_fee_details_to_bank(company):
	send_fee_details_to_bank = frappe.get_value("Company", company, "send_fee_details_to_bank") or 0
	if not send_fee_details_to_bank:
		return False
	else:
		return True
