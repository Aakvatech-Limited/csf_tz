# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

import json
import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from csf_tz.vfd_support.sales_invoice import get_item_taxcode, remove_all_except_numbers

SETTINGS_DOCTYPE = "Pergamon VFD Settings"
TAX_CODES = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
TIMEOUT = (5, 60)


class PergamonVFDSettings(Document):
	pass


def get_provider():
	name = frappe.db.get_value("VFD Provider", {"vfd_provider_settings": SETTINGS_DOCTYPE})
	if not name:
		frappe.throw(_("Configure a VFD Provider for Pergamon VFD Settings"))
	return frappe.get_cached_doc("VFD Provider", name)


def get_line_amount(item, tax_code):
	"""Total VFD VAT-inclusive detection, with base_rate as the starting rate.

	For VAT code A the existing Total VFD rule treats base_amount as VAT
	inclusive when it differs from base_net_amount + distributed discount.
	Otherwise 18% VAT is added to base_rate * qty. Other VAT groups use
	base_rate * qty without adding VAT.
	"""
	qty = flt(item.qty)
	if qty <= 0:
		frappe.throw(_("Pergamon requires a positive quantity on every line"))
	base_rate = flt(item.base_rate)
	base_amount = flt(item.base_amount)
	base_net_amount = flt(item.base_net_amount)
	distributed_discount = flt(item.get("distributed_discount_amount", 0))

	if tax_code == "A":
		if flt(base_net_amount + distributed_discount, 2) != flt(base_amount, 2):
			return flt(base_amount, 2)
		return flt(base_rate * qty * 1.18, 2)

	return flt(base_rate * qty, 2)


def normalize_customer_id(value):
	"""Avoid trailing .0 on numeric identifiers imported through spreadsheets."""
	value = str(value or "").strip()
	if value.endswith(".0") and value[:-2].isdigit():
		return value[:-2]
	return value


def get_payload(doc):
	"""Build the Pergamon receipt using base rates and Total VFD VAT rules.

	All values are in company/base currency; discounts are always zero.
	The base-currency amount must reconcile to the base invoice total.
	"""
	company_currency = frappe.get_cached_value("Company", doc.company, "default_currency")
	if company_currency != "TZS":
		frappe.throw(_("Pergamon requires company base currency TZS; found {0}").format(company_currency))
	lines = []
	for item in doc.items:
		code = TAX_CODES[get_item_taxcode(item.item_tax_template, item.item_code, doc.name)]
		gross = get_line_amount(item, code)
		lines.append(
			{
				"name": item.item_name or item.item_code,
				"qty": flt(item.qty),
				"unitPrice": flt(gross / flt(item.qty), 6),
				"amount": gross,
				"discount": 0,
				"taxCode": code,
			}
		)

	total = flt(sum(row["amount"] for row in lines), 2)
	if abs(total - flt(doc.base_grand_total, 2)) > 0.05:
		frappe.throw(
			_("Pergamon item totals do not match Sales Invoice base grand total; check taxes and discounts")
		)

	id_type = str(doc.vfd_cust_id_type or "6")[:1]
	return {
		"traderInvoiceNo": doc.name,
		"totalAmount": total,
		"paymentType": "CASH",
		"custIdType": id_type,
		"custId": normalize_customer_id(doc.vfd_cust_id),
		"custName": doc.customer_name or doc.customer,
		"custPhone": remove_all_except_numbers(doc.get("contact_mobile") or ""),
		"currency": "TZS",
		"exchangeRate": 1.0,
		"dateTime": str(doc.get("posting_date")) + " " + str(doc.get("posting_time") or "00:00:00")[:8],
		"salesItems": lines,
	}


def validate_postable(doc):
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted Sales Invoices can be sent to Pergamon"))
	if doc.is_return or doc.is_not_vfd_invoice or doc.vfd_status == "Success":
		frappe.throw(_("This Sales Invoice is ineligible or already fiscalised"))
	# Timeouts may occur after the provider has already created the receipt.
	# Require manual reconciliation instead of blindly sending a duplicate.
	if frappe.db.exists("VFD Provider Posting", {"sales_invoice": doc.name}):
		frappe.throw(_("A VFD posting already exists. Reconcile with Pergamon before resending."))


def parse_receipt(response):
	"""Fail closed until a documented acceptance response is supplied."""
	data = response.get("data") if isinstance(response.get("data"), dict) else response
	accepted = data.get("success") is True or str(data.get("status", "")).upper() in ("SUCCESS", "ACCEPTED")
	verification = data.get("verificationCode") or data.get("traReceiptVerificationCode")
	if not accepted or not verification:
		return False, data
	return True, data


@frappe.whitelist()
def post_fiscal_receipt(doc=None, method="POST", payload=None, invoice_id=None, preview=False):
	if not doc:
		if not invoice_id:
			frappe.throw(_("Sales Invoice is required"))
		doc = frappe.get_doc("Sales Invoice", invoice_id)
		doc.check_permission("read")
	validate_postable(doc)
	settings = frappe.get_doc(SETTINGS_DOCTYPE, doc.company)
	provider = get_provider()
	selected = frappe.db.get_value("Company VFD Provider", doc.company, "vfd_provider")
	if selected != provider.name:
		frappe.throw(_("Pergamon is not the selected VFD provider for this company"))
	if provider.sandbox:
		frappe.throw(_("Pergamon sandbox endpoint is not configured. Disable Sandbox before posting."))
	if not provider.base_url.lower().startswith("https://"):
		frappe.throw(_("Pergamon endpoint must use HTTPS"))
	url = provider.base_url.rstrip("/") + provider.get_endpoint("post_receipt")
	# Always rebuild the payload on the server; the preview is not trusted input.
	request_data = get_payload(doc)
	safe_headers = {"Accept": "application/json", "Content-Type": "application/json"}
	try:
		response = requests.post(
			url,
			json=request_data,
			headers=safe_headers,
			auth=(settings.username, settings.get_password("password")),
			timeout=TIMEOUT,
		)
		try:
			result = response.json()
		except ValueError:
			result = {"message": "Non-JSON response from Pergamon"}
		if not isinstance(result, dict):
			result = {"message": "Unexpected Pergamon response type"}
	except requests.RequestException:
		# No automatic retry: request may have reached the fiscal server.
		result, response = (
			{"message": "Transport outcome uncertain; reconcile with Pergamon before retry"},
			None,
		)

	accepted, receipt = parse_receipt(result)
	accepted = bool(accepted and response is not None and response.ok)
	posting = frappe.new_doc("VFD Provider Posting")
	posting.sales_invoice = doc.name
	posting.req_data = json.dumps(request_data)
	posting.req_headers = json.dumps(safe_headers)  # never persist Basic Auth
	posting.ackcode = response.status_code if response is not None else 0
	posting.ackmsg = json.dumps(result)
	posting.date = now_datetime().date()
	posting.time = now_datetime().time()
	if accepted:
		receipt_number = receipt.get("receiptNumber") or receipt.get("rctNum")
		if str(receipt_number or "").isdigit():
			posting.rctnum = int(receipt_number)
	posting.insert(ignore_permissions=True)

	values = {"vfd_status": "Success" if accepted else "Failed", "vfd_posting_info": posting.name}
	if accepted:
		values.update(
			{
				"vfd_rctvnum": receipt.get("verificationCode") or receipt.get("traReceiptVerificationCode"),
				"vfd_verification_url": receipt.get("verificationUrl")
				or receipt.get("traReceiptVerificationUrl"),
				"vfd_date": posting.date,
				"vfd_time": posting.time,
			}
		)
	if method == "on_submit":
		doc.update(values)
		doc.save(ignore_permissions=True)
	else:
		frappe.db.set_value("Sales Invoice", doc.name, values)
	return {"data": result, "vfd_provider": provider.name, "preview": preview, "success": accepted}
