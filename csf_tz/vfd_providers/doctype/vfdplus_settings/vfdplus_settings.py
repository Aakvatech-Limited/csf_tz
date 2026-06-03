# Copyright (c) 2023, Aakvatech Limited and contributors
# For license information, please see license.txt

# import frappe
import json
from time import sleep

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, format_datetime, nowdate, nowtime

from csf_tz.vfd_providers.utils import get_vat_amount


class VFDPlusSettings(Document):
	def validate(self):
		get_serial_info(self, method="validate")


# Below are the status codes returned by VFDPlus API
vfdplus_status_codes = {
	"4000": "VFDPLUS-API-KEY not found in header!",
	"4001": "Invalid VFDPLUS-API-KEY!",
	"4002": "VFDPLUS-API-KEY expired!",
	"4003": "VFDPLUS-API-KEY not enabled!",
	"4004": "VFDPLUS-API-KEY is deleted!",
	"4005": "VFDPLUS-API-KEY does not match any vfd-plus-account!",
	"4006": "VFDPLUS-API-KEY does not match any vfd-plus-serial/credential!",
	"4007": "Serial/Credential is not active!",
	"4008": "TRA Serial Supplied is not activated!",
	"4009": "Device Cannot generate receipt,Device is still off",
	"4010": "TRA Supplied serial is expired; Please contact Our Customer-Service Team for Renewal Process.",
	"4011": "VFDPlus Accpount Expired",
	"4012": "Invalid Receipt JSON Format,check missing fields,read all instructions supplied per each error line",
	"4013": "Only single receipt can be posted at a time",
	"4014": "Discount setting on device is not enabled",
	"4015": "Invoice/Receipt for a given serial is already posted",
	"2000": "Receipt Posted OK, OK Response",
}


def send_vfdplus_request(
	call_type,
	company,
	payload=None,
	type="GET",
	vfdplus_settings=None,
	vfd_provider_posting_doc=None,
):
	"""Send request to VFDPlus API
	Parameters
	----------
	call_type : str
	Type of call to make. e.g. "get_serial_info", "post_fiscal_receipt", "account_info", etc.
	company : str
	Company to get VFDPlus settings from
	payload : dict
	Payload to send to VFDPlus API
	type : str
	Type of request to make. e.g. "GET", "POST", "PUT", etc.
	vfdplus_settings : object
	Python object which is expected to be from VFDPlus Settings doctype.
	vfd_provider_posting_doc : object
	Python object which is expected to be from VFD Provider Posting doctype.

	Returns
	-------
	data : dict
	Dictionary with response from VFDPlus API
	"""
	vfdplus = frappe.get_cached_doc("VFD Provider", "VFDPlus")
	if not vfdplus:
		frappe.throw(_("VFDPlus is not setup!"))
	if not vfdplus_settings:
		vfdplus_settings = frappe.get_doc("VFDPlus Settings", company)
	url = (
		vfdplus.base_url
		+ frappe.get_all(
			"VFD Provider Attribute",
			filters={"parent": "VFDPlus", "key": call_type},
			fields=["value"],
			ignore_permissions=True,
		)[0].value
	)
	headers = {
		"VFDPLUS-API-KEY": vfdplus_settings.vfdplus_api_key,
		"Content-Type": "application/json",
	}

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
				if data.get("msg_status") != "OK" and not (
					data.get("msg_status") == "WARNING" and data.get("msg_code") == 4015
				):
					frappe.throw(_(f"Error returned from VFDPlus: {data.get('msg_code')}"))
				else:
					frappe.log_error(
						title="Send Request OK",
						message=f"Send Request: {url} - Status Code: {res.status_code}\n{res.text}",
					)
			else:
				data = []
				frappe.log_error(
					title="Send Request Error",
					message=f"Send Request: {url} - Status Code: {res.status_code}\n{res.text}",
				)
				frappe.throw(f"Error is {res.text}")
			if vfd_provider_posting_doc:
				vfd_provider_posting_doc.req_headers = (
					json.dumps(headers, ensure_ascii=False).replace("\\'", "'").replace('\\"', '"')
				)
				vfd_provider_posting_doc.req_data = (
					json.dumps(payload, ensure_ascii=False).replace("\\'", "'").replace('\\"', '"')
				)
				vfd_provider_posting_doc.ackcode = data["msg_code"]
				vfd_provider_posting_doc.ackmsg = (
					str(data["msg_data"]).replace("\\'", "'").replace('\\"', '"')
				)

			break
		except Exception as e:
			sleep(3 * i + 1)
			if i != 2:
				continue
			else:
				frappe.log_error(
					message=frappe.get_traceback(),
					title=str(e)[:140] if e else "Send VFDPLus Request Error",
				)
				frappe.throw(f"Connection failure is {res.text}")
				raise e
	return data


def get_payload(doc):
	"""Generate payload for VFDPlus API
	Parameters
	----------
	doc : object
	Python object which is expected to be from Sales Invoice doctype.

	Returns
	-------
	payload : dict
	Dictionary with payload for VFDPlus API
	"""

	cart_items = []
	total_amount = 0
	tax_map = {"1": "A", "2": "B", "3": "C", "4": "D", "5": "E"}

	for item in doc.items:
		vat_rate_id = frappe.get_cached_value("Item Tax Template", item.item_tax_template, "vfd_taxcode")[:1]

		vat_rate_code = tax_map[vat_rate_id]

		sp = get_vat_amount(item, vat_rate_code, precision=2)

		cart_items.append(
			{
				"vat_rate_code": vat_rate_code,
				"vat_rate_id": vat_rate_id,
				"item_name": item.item_code,
				"item_barcode": "-1",
				"item_qty": item.qty,
				"usp": flt(sp / item.qty, 2),
				"sp": sp,
				"unit_discount_perc": 0.0,
				"unit_discount_amt": 0.0,
				"total_item_discount": 0.0,
			}
		)
		total_amount += sp

	vfdplus_settings = frappe.get_doc("VFDPlus Settings", doc.company)

	payload = {
		"credential_code": vfdplus_settings.serial_code,
		"branch_id": "",
		"depart_id": "",
		"trans_no": doc.name,
		"idate": str(doc.vfd_date or nowdate()),
		"itime": format_datetime(str(doc.vfd_time or nowtime()), "HH:mm:ss"),
		"customer_info": {
			"cust_name": doc.customer_name,
			"cust_id_type": doc.vfd_cust_id_type or "6",
			"cust_id": doc.vfd_cust_id or "NIL",
			"cust_phone": "",
			"cust_vrn": "",
			"cust_addr": "",
			"id_for": "",
		},
		"payment_methods": [{"pmt_type": "INVOICE", "pmt_amount": flt(total_amount, 2)}],
		"cart_totals": {
			"item_counts": len(doc.items),
			"total_amount": flt(total_amount, 2),
			"total_amount_exclude_discount": flt(total_amount, 2),
			"discount": 0.0,
		},
		"cart_items": cart_items,
		"user_info": {
			"user_id": "1",
			"username": doc.modified_by.split("@")[0],
			"till_id": "1",
		},
	}

	return payload


@frappe.whitelist()
def post_fiscal_receipt(
	doc: str = None, method: str = "POST", payload: str = {}, invoice_id: str = None, preview: str = False
):
	"""Post fiscal receipt to VFDPlus
	Parameters
	----------
	doc : object
	Python object which is expected to be from VFDPlus Settings doctype.
	method : str
	Method name which is calling this function. e.g. POST, validate, on_update, etc.

	Returns
	-------
	data : dict
	Dictionary with response from VFDPlus API
	"""

	if not doc and not invoice_id:
		frappe.throw(_("Sales Invoice is required!"))

	if not doc and invoice_id:
		doc = frappe.get_doc("Sales Invoice", invoice_id)

	doc.vfd_date = doc.vfd_date or nowdate()
	doc.vfd_time = format_datetime(str(nowtime()), "HH:mm:ss")

	if not payload:
		payload = get_payload(doc)

		# Convert the payload to JSON string format because it is not comming from frontend where it is already in JSON string format
		payload = json.dumps(payload)

	vfd_provider_posting_doc = frappe.new_doc("VFD Provider Posting")

	data = send_vfdplus_request(
		"post_fiscal_receipt",
		doc.company,
		payload,
		"POST",
		vfd_provider_posting_doc=vfd_provider_posting_doc,
	)

	vfd_provider_posting_doc.sales_invoice = doc.name
	vfd_provider_posting_doc.rctnum = doc.vfd_rctvnum
	vfd_provider_posting_doc.date = doc.vfd_date
	vfd_provider_posting_doc.time = doc.vfd_time
	vfd_provider_posting_doc.save(ignore_permissions=True)

	rctvnum = data["msg_data"].get("rctvnum")
	verification_url = (
		f"https://verify.tra.go.tz/{rctvnum}_{str(data['msg_data'].get('itime')).replace(':','')}"
	)

	if method == "on_submit":
		doc.vfd_status = "Success"
		doc.vfd_rctvnum = rctvnum
		doc.vfd_date = data["msg_data"].get("idate")
		doc.vfd_time = data["msg_data"].get("itime")
		doc.vfd_verification_url = verification_url
		doc.vfd_posting_info = vfd_provider_posting_doc.name

		doc.save()

	elif method == "POST":
		frappe.db.set_value("Sales Invoice", doc.name, "vfd_rctvnum", rctvnum)
		frappe.db.set_value("Sales Invoice", doc.name, "vfd_status", "Success")
		frappe.db.set_value("Sales Invoice", doc.name, "vfd_date", data["msg_data"].get("idate"))
		frappe.db.set_value("Sales Invoice", doc.name, "vfd_time", data["msg_data"].get("itime"))
		frappe.db.set_value("Sales Invoice", doc.name, "vfd_posting_info", vfd_provider_posting_doc.name)
		frappe.db.set_value("Sales Invoice", doc.name, "vfd_verification_url", verification_url)

	return {"data": data, "vfd_provider": "VFDPlus", "preview": preview}


def get_serial_info(doc, method):
	"""Get serial info from VFDPlus
	Parameters
	----------
	doc : object
	Python object which is expected to be from VFDPlus Settings doctype.
	method : str
	Method name which is calling this function. e.g. validate, on_update, etc.

	Returns
	-------
	Nothing
	"""
	data = send_vfdplus_request(
		call_type="serial_info",
		company=doc.company,
		type="GET",
		vfdplus_settings=doc,
		vfd_provider_posting_doc=None,
	)
	if data:
		doc.response = str(data["msg_data"])
		for key, value in data["msg_data"].items():
			try:
				setattr(doc, key, value)
			except Exception as e:
				frappe.log_error(
					message=frappe.get_traceback(),
					title="Error in set attribute for VFDPlus",
				)
				raise e
	if method != "validate":
		doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_account_info(company: str):
	"""Get serial info from VFDPlus
	Parameters
	----------
	company : str
	String having Company name

	Returns
	-------
	data : dict
	Dictionary of account info
	"""
	# TODO
	data = send_vfdplus_request(call_type="account_info", company=company, type="GET")
	if data:
		return data
	else:
		frappe.throw(_(f"No data returned from VFDPlus for company: {company}"))
