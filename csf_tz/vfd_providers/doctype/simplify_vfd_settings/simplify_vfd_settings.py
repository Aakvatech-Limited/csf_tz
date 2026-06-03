# Copyright (c) 2023, Aakvatech Limited and contributors
# For license information, please see license.txt

import json
from datetime import datetime
from time import sleep

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_to_date,
	flt,
	format_datetime,
	now_datetime,
	nowdate,
	nowtime,
)

from csf_tz.vfd_providers.utils import get_vat_amount

# The process of getting the access token and refresh token is as follows:
# 1. Call the login endpoint with username and password to get the access token and refresh token.
# 2. Store the access token and refresh token in the Simplify VFD Settings
# 3. Set the token expiration time to 20 minutes from now for the access token
# 5. If the access token is expired, call the refresh token endpoint with the refresh token
# 6. If the refresh token is expired (after 24 hours), call the login endpoint again to get a new refresh token.


class SimplifyVFDSettings(Document):
	@frappe.whitelist()
	def get_bearer_token(self):
		"""Get bearer token from Simplify VFD"""

		if not self.username or not self.password:
			frappe.throw(_("Username and Password are required!"))

		payload = {
			"username": self.username,
			"password": self.get_password(),
		}

		data = send_simplify_vfd_request("login", self.company, json.dumps(payload), "POST")

		token = data.get("token")
		if not token:
			frappe.throw(_("Invalid username or password!"))

		refresh_token = data.get("refresh_token")
		token_expires = add_to_date(now_datetime(), minutes=20)

		self.db_set("bearer_token", token)
		self.db_set("refresh_token", refresh_token)
		self.db_set("token_expires", token_expires)

		self.clear_cache()
		self.reload()
		return True

	def refresh_bearer_token(self):
		"""Refresh bearer token from Simplify VFD"""

		if not self.refresh_token:
			frappe.throw(
				_("Refresh Token is not found, Please set username and password and generate the token!")
			)

		payload = {
			"refresh_token": self.get_password("refresh_token"),
		}

		data = send_simplify_vfd_request("refresh", self.company, json.dumps(payload), "POST")
		token = data.get("token")
		refresh_token = data.get("refresh_token")

		if not token or not refresh_token:
			frappe.throw(_("Invalid refresh token!"))

		token_expires = add_to_date(now_datetime(), minutes=20)
		self.db_set("bearer_token", token)
		self.db_set("refresh_token", refresh_token)
		self.db_set("token_expires", token_expires)

		self.clear_cache()
		self.reload()
		return True


def get_access_token():
	"""Refresh access token from Simplify VFD"""

	setting_companies = frappe.get_all("Simplify VFD Settings", fields=["name"], pluck="name")

	for company in setting_companies:
		doc = None
		if frappe.db.exists("Simplify VFD Settings", company):
			doc = frappe.get_cached_doc("Simplify VFD Settings", company)
		else:
			continue

		if doc.token_expires and doc.token_expires <= now_datetime():
			doc.refresh_bearer_token()


def get_refresh_token():
	"""Fetch refresh token from Simplify VFD"""

	setting_companies = frappe.get_all("Simplify VFD Settings", fields=["name"], pluck="name")

	for company in setting_companies:
		doc = None
		if frappe.db.exists("Simplify VFD Settings", company):
			doc = frappe.get_cached_doc("Simplify VFD Settings", company)
		else:
			continue

		doc.get_bearer_token()


@frappe.whitelist()
def get_payload(doc: str):
	"""Generate payload for Simplify VFD"""

	items = []
	total_amount = 0

	tax_map = {
		"1": "STANDARD",
		"2": "SPECIAL_RATE",
		"3": "ZERO_RATED",
		"4": "SPECIAL_RELIEF",
		"5": "EXEMPTED",
	}
	vfd_cust_id_type_map = {
		"1": "TAX_IDENTIFICATION_NUMBER",
		"2": "DRIVING_LICENCE",
		"3": "VOTERS_NUMBER",
		"4": "PASSPORT",
		"5": "NATIONAL_IDENTIFICATION_AUTHORITY",
		"6": "NO_IDENTIFICATION",
	}

	for item in doc.items:
		vfd_taxcode = frappe.get_cached_value("Item Tax Template", item.item_tax_template, "vfd_taxcode")

		vat_rate_id = vfd_taxcode[:1] if vfd_taxcode else "1"

		vat_group = tax_map[vat_rate_id]

		price = get_vat_amount(item, vat_rate_id, precision=2)

		unit_price = flt((price / item.qty), 2)

		items.append(
			{
				"description": f"{item.item_code} - {item.item_name}"
				if item.item_name != item.item_code
				else item.item_code,
				"quantity": item.qty,
				"unitAmount": unit_price,
				"discountRate": 0.0,
				"taxType": vat_group,
			}
		)

		total_amount += flt((unit_price * item.qty), 2)

	payments = [{"type": "INVOICE", "amount": flt(total_amount, 2)}]

	vfd_cust_id_type = doc.vfd_cust_id_type[:1] if doc.vfd_cust_id_type else "6"
	payload = {
		"dateTime": str(doc.vfd_date or nowdate()),
		"customer": {
			"identificationType": vfd_cust_id_type_map[vfd_cust_id_type],
			"identificationNumber": doc.vfd_cust_id if vfd_cust_id_type != "6" else "",
			"vatRegistrationNumber": doc.tax_id or "",
			"name": doc.customer_name,
			"mobileNumber": "",
			"email": "",
		},
		"invoiceAmountType": "INCLUSIVE",
		"items": items,
		"payments": payments,
		"partnerInvoiceId": doc.name,
	}

	return payload


@frappe.whitelist()
def post_fiscal_receipt(
	doc: str = None, method: str = "POST", payload: str = {}, invoice_id: str = None, preview: str = False
):
	"""Post fiscal receipt to Simplify VFD
	Parameters
	----------
	doc : object
	Python object which is expected to be from Sales Invoice doctype.
	method : str
	Method name which is calling this function. e.g. POST, validate, on_update, etc.
	payload : dict
	Payload to send to Simplify VFD API
	invoice_id : str
	Sales Invoice ID to post fiscal receipt for. If doc is not provided, this parameter is required.

	Returns
	-------
	res_data : dict
	Dictionary with response from Simplify VFD API
	"""

	if not doc and not invoice_id:
		frappe.throw(_("Sales Invoice is required!"))

	if not doc and invoice_id:
		doc = frappe.get_doc("Sales Invoice", invoice_id)

	simplify_vfd_settings = frappe.get_doc("Simplify VFD Settings", doc.company)
	if simplify_vfd_settings.token_expires and simplify_vfd_settings.token_expires <= now_datetime():
		simplify_vfd_settings.refresh_bearer_token()

	doc.vfd_date = doc.vfd_date or nowdate()
	doc.vfd_time = format_datetime(str(nowtime()), "HH:mm:ss")

	if not payload:
		payload = get_payload(doc)

		# Convert the payload to JSON string format because it is not comming from frontend where it is already in JSON string format
		payload = json.dumps(payload)

	vfd_provider_posting_doc = frappe.new_doc("VFD Provider Posting")

	data = send_simplify_vfd_request(
		"createIssuedInvoice",
		doc.company,
		payload,
		"POST",
		for_vfd_posting=True,
	)

	res_data = data.get("message")
	if res_data.get("success"):
		dt_object = datetime.strptime(res_data.get("issuedAt"), "%Y-%m-%d %H:%M:%S")

		# Extract date and time
		date_part = dt_object.date()
		time_part = dt_object.time()

	else:
		date_part = nowdate()
		time_part = nowtime()

	vfd_provider_posting_doc.sales_invoice = doc.name
	vfd_provider_posting_doc.rctnum = doc.vfd_rctvnum
	vfd_provider_posting_doc.req_headers = str(data.get("headers"))
	vfd_provider_posting_doc.ackmsg = str(res_data)
	vfd_provider_posting_doc.ackcode = data.get("status_code")
	vfd_provider_posting_doc.date = date_part
	vfd_provider_posting_doc.time = time_part
	vfd_provider_posting_doc.req_data = payload

	vfd_provider_posting_doc.save(ignore_permissions=True)

	if method == "on_submit":
		doc.vfd_status = "Success" if res_data.get("success") else "Failed"
		doc.vfd_verification_url = res_data.get("verificationUrl")
		doc.vfd_rctvnum = res_data.get("verificationCode")
		doc.vfd_date = date_part
		doc.vfd_time = time_part
		doc.vfd_posting_info = vfd_provider_posting_doc.name
		doc.save(ignore_permissions=True)
		doc.add_comment(
			"Comment",
			f"VFD Invoice ID: {res_data.get('invoiceId')}",
		)

	elif method == "POST":
		frappe.db.set_value(
			"Sales Invoice",
			doc.name,
			{
				"vfd_rctvnum": res_data.get("verificationCode"),
				"vfd_status": "Success",
				"vfd_verification_url": res_data.get("verificationUrl"),
				"vfd_date": date_part,
				"vfd_time": time_part,
				"vfd_posting_info": vfd_provider_posting_doc.name,
			},
		)
		doc.add_comment(
			"Comment",
			f"VFD Invoice ID: {res_data.get('invoiceId')}",
		)

	return {"data": res_data, "vfd_provider": "SimplifyVFD", "preview": preview}


def send_simplify_vfd_request(
	call_type,
	company,
	payload=None,
	type="GET",
	simplify_vfd_settings=None,
	for_vfd_posting=False,
):
	"""Send request to Simplify VFD API
	Parameters
	----------
	call_type : str
	Type of call to make. e.g. "get_serial_info", "post_fiscal_receipt", "account_info", etc.
	company : str
	Company to get Simplify VFD settings from
	payload : dict
	Payload to send to Simplify VFD API
	type : str
	Type of request to make. e.g. "GET", "POST", "PUT", etc.
	simplify_vfd_settings : object
	Python object which is expected to be from Simplify VFD Settings doctype.
	for_vfd_posting : Boolean
	If True, will return headers along with response data. Default is False.

	Returns
	-------
	data : dict
	Dictionary with response from Simplify VFD API
	"""
	simplify_vfd = frappe.get_cached_doc("VFD Provider", "SimplifyVFD")

	if not simplify_vfd_settings:
		simplify_vfd_settings = frappe.get_cached_doc(simplify_vfd.vfd_provider_settings, company)

	simplify_vfd_endpoint = [row for row in simplify_vfd.attributes if row.key == call_type][0].value

	url = f"{simplify_vfd.base_url.strip()}{simplify_vfd_endpoint.strip()}"

	headers = {
		"accept": "application/json",
		"Content-Type": "application/json",
	}
	if call_type not in ["login", "refresh"]:
		headers["Authorization"] = f"Bearer {simplify_vfd_settings.get_password('bearer_token')}"

	data = None
	for i in range(3):
		try:
			res = requests.request(
				method=type,
				url=url,
				data=payload if payload else None,
				headers=headers,
				timeout=500,
			)
			if res.ok:
				data = json.loads(res.text)
			else:
				data = []
				frappe.log_error(
					title="Send Request Error",
					message=f"Send Request: {url} - Status Code: {res.status_code}\n{res.text}\n{payload}",
				)
				frappe.throw(f"Error is {res.text}")

			break
		except Exception as e:
			sleep(3 * i + 1)
			if i != 2:
				continue
			else:
				frappe.log_error(
					message=frappe.get_traceback(),
					title=str(e)[:140] if e else "Send Simplify VFD Request Error",
				)
				raise e

	if for_vfd_posting:
		data = {
			"message": data,
			"headers": headers,
			"status_code": res.status_code,
		}
		return data

	return data
