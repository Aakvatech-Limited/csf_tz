# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

import json
from pathlib import Path
from urllib.parse import quote
import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime

from csf_tz.vfd_support.sales_invoice import get_item_taxcode, remove_all_except_numbers

SETTINGS_DOCTYPE = "Pergamon VFD Settings"
TAX_CODES = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
TIMEOUT = (5, 60)


def get_tls_verify():
	"""Use the system trust store or an explicitly configured private CA bundle.

	Configure pergamon_ca_bundle in site_config.json. TLS verification remains
	enabled and certificate hostname/IP validation is enforced by requests.
	"""
	ca_bundle = frappe.conf.get("pergamon_ca_bundle")
	if not ca_bundle:
		return True
	path = Path(str(ca_bundle))
	if not path.is_absolute() or not path.is_file():
		frappe.throw(_("Pergamon CA bundle must be an existing absolute PEM file path"))
	return str(path)


def raise_tls_error():
	frappe.throw(
		_(
			"Pergamon HTTPS certificate verification failed. Configure a trusted "
			"certificate for the Pergamon server or set pergamon_ca_bundle to a "
			"trusted PEM CA file in the site's configuration. SSL verification "
			"must remain enabled."
		)
	)


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


def get_fiscal_datetime(fiscal_datetime=None):
	"""Format the site-local timestamp used for the actual fiscal submission."""
	return (fiscal_datetime or now_datetime()).strftime("%Y-%m-%d %H:%M:%S")


def get_payload(doc, fiscal_datetime=None):
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
	base_grand_total = flt(doc.base_grand_total, 2)
	base_rounded_total = flt(doc.get("base_rounded_total") or base_grand_total, 2)
	base_rounding_adjustment = flt(doc.get("base_rounding_adjustment") or 0, 2)
	if abs(base_grand_total + base_rounding_adjustment - base_rounded_total) > 0.01:
		frappe.throw(_("Pergamon base rounded total does not match the rounding adjustment"))
	if abs(total - base_rounded_total) > 0.05:
		frappe.throw(
			_("Pergamon item totals do not match Sales Invoice base rounded total; check taxes and discounts")
		)

	id_type_value = str(doc.get("vfd_cust_id_type") or "").strip()
	id_type = id_type_value.split("-", 1)[0].strip()
	if not id_type.isdigit() or len(id_type) != 1:
		frappe.throw(_("Select a valid VFD Customer ID Type before sending to Pergamon"))
	customer_id = normalize_customer_id(doc.get("vfd_cust_id"))
	if not customer_id:
		frappe.throw(_("Enter a VFD Customer ID before sending to Pergamon"))
	return {
		"traderInvoiceNo": doc.name,
		"totalAmount": total,
		"paymentType": "CASH",
		"custIdType": id_type,
		"custId": customer_id,
		"custName": doc.customer_name or doc.customer,
		"custPhone": remove_all_except_numbers(doc.get("contact_mobile") or ""),
		"currency": "TZS",
		"exchangeRate": 1.0,
		"dateTime": get_fiscal_datetime(fiscal_datetime),
		"salesItems": lines,
	}


def validate_postable(doc):
	"""Use the normal VFD retry lifecycle, consistent with Total VFD."""
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted Sales Invoices can be sent to Pergamon"))
	if doc.is_return or doc.is_not_vfd_invoice or doc.vfd_status == "Success":
		frappe.throw(_("This Sales Invoice is ineligible or already fiscalised"))


def receipt_field(response, *names):
	"""Read receipt fields from documented-style response envelopes, without inventing values."""
	if not isinstance(response, dict):
		return None
	for data in (
		response.get("data"),
		response.get("receipt"),
		response.get("result"),
		response,
	):
		if not isinstance(data, dict):
			continue
		for name in names:
			if data.get(name):
				return data[name]
	return None


def get_verification_code(response):
	return receipt_field(
		response, "receipVerificationNo", "verificationCode", "traReceiptVerificationCode"
	)


def get_verification_url(response):
	return receipt_field(
		response, "invoiceVerificationUrl", "verificationUrl", "traReceiptVerificationUrl"
	)


def parse_receipt(response):
	"""Recognize the actual Pergamon SUCCES response, including existing receipts."""
	if not isinstance(response, dict):
		return False, response
	success = receipt_field(response, "success") is True
	status = str(receipt_field(response, "statusCode", "status") or "").upper()
	return bool((success or status in ("SUCCES", "SUCCESS", "ACCEPTED")) and get_verification_code(response)), response


def get_receipt_timestamp(response, fallback):
	"""Use the original provider receipt timestamp when it is supplied."""
	from datetime import datetime

	value = receipt_field(response, "dateTime")
	if value:
		try:
			return datetime.strptime(str(value), "%Y%m%d%H%M%S")
		except ValueError:
			pass
	return fallback


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
	fiscal_datetime = now_datetime()
	request_data = get_payload(doc, fiscal_datetime=fiscal_datetime)
	safe_headers = {"Accept": "application/json", "Content-Type": "application/json"}
	try:
		response = requests.post(
			url,
			json=request_data,
			headers=safe_headers,
			auth=(settings.username, settings.get_password("password")),
			timeout=TIMEOUT,
			verify=get_tls_verify(),
		)
		try:
			result = response.json()
		except ValueError:
			result = {"message": "Non-JSON response from Pergamon"}
		if not isinstance(result, dict):
			result = {"message": "Unexpected Pergamon response type"}
	except requests.exceptions.SSLError:
		# TLS verification fails before an authenticated HTTP request is sent.
		result, response = (
			{"message": "Pergamon HTTPS certificate verification failed; configure a trusted CA certificate"},
			None,
		)
	except requests.RequestException:
		# No automatic retry: request may have reached the fiscal server.
		result, response = (
			{"message": "Transport outcome uncertain; reconcile with Pergamon before retry"},
			None,
		)

	accepted, receipt = parse_receipt(result)
	accepted = bool(accepted and response is not None and response.ok)
	if accepted:
		reference = receipt_field(receipt, "traderInvoiceNo")
		amount = receipt_field(receipt, "totalAmount")
		currency = receipt_field(receipt, "currency")
		accepted = bool(
			str(reference or "") == doc.name
			and amount is not None
			and abs(flt(amount, 2) - flt(request_data["totalAmount"], 2)) <= 0.05
			and currency == "TZS"
		)
	receipt_datetime = get_receipt_timestamp(receipt, fiscal_datetime) if accepted else fiscal_datetime
	posting = frappe.new_doc("VFD Provider Posting")
	posting.sales_invoice = doc.name
	posting.req_data = json.dumps(request_data)
	posting.req_headers = json.dumps(safe_headers)  # never persist Basic Auth
	posting.ackcode = response.status_code if response is not None else 0
	posting.ackmsg = json.dumps(result)
	posting.date = fiscal_datetime.date()
	posting.time = fiscal_datetime.time().replace(microsecond=0)
	if accepted:
		receipt_number = receipt_field(receipt, "receiptNo", "receiptNumber", "rctNum")
		if str(receipt_number or "").isdigit():
			posting.rctnum = int(receipt_number)
	posting.insert(ignore_permissions=True)

	values = {"vfd_status": "Success" if accepted else "Failed", "vfd_posting_info": posting.name}
	if accepted:
		values.update(
			{
				"vfd_rctvnum": get_verification_code(receipt),
				"vfd_verification_url": get_verification_url(receipt),
				"vfd_date": receipt_datetime.date(),
				"vfd_time": receipt_datetime.time().replace(microsecond=0),
			}
		)
	if method == "on_submit":
		doc.update(values)
		doc.save(ignore_permissions=True)
	else:
		frappe.db.set_value("Sales Invoice", doc.name, values)
	return {"data": result, "vfd_provider": provider.name, "preview": preview, "success": accepted}


@frappe.whitelist()
def get_pergamon_invoice(provider_invoice_id, sales_invoice=None):
	"""Fetch one Pergamon invoice by its provider ID, without fiscalizing again.

	The Postman collection does not define the GET response schema or prove
	that its ID is the ERPNext Sales Invoice name. Never infer that mapping.
	"""
	provider_invoice_id = str(provider_invoice_id or "").strip()
	if not provider_invoice_id or len(provider_invoice_id) > 128 or "/" in provider_invoice_id:
		frappe.throw(_("Enter a valid Pergamon invoice ID"))

	if not sales_invoice:
		frappe.throw(_("Select the Sales Invoice for verification"))
	doc = frappe.get_doc("Sales Invoice", sales_invoice)
	doc.check_permission("read")

	provider = get_provider()
	selected = frappe.db.get_value("Company VFD Provider", doc.company, "vfd_provider")
	if selected != provider.name:
		frappe.throw(_("Pergamon is not the selected VFD provider for this company"))
	if provider.sandbox:
		frappe.throw(_("Pergamon sandbox endpoint is not configured"))
	if not provider.base_url.lower().startswith("https://"):
		frappe.throw(_("Pergamon endpoint must use HTTPS"))
	endpoint = provider.get_endpoint("get_invoice")
	if endpoint != "/invoices/{id}":
		frappe.throw(_("Unexpected Pergamon invoice lookup endpoint configuration"))
	settings = frappe.get_doc(SETTINGS_DOCTYPE, doc.company)
	url = provider.base_url.rstrip("/") + endpoint.replace("{id}", quote(provider_invoice_id, safe=""))
	try:
		response = requests.get(
			url,
			headers={"Accept": "application/json"},
			auth=(settings.username, settings.get_password("password")),
			timeout=TIMEOUT,
			verify=get_tls_verify(),
		)
	except requests.exceptions.SSLError:
		raise_tls_error()
	except requests.RequestException:
		frappe.throw(_("Pergamon invoice lookup failed. Check connectivity and retry."))

	if response.status_code == 404:
		return {"found": False, "verified": False, "message": _("Invoice ID not found at Pergamon")}
	if not response.ok:
		frappe.throw(
			_("Pergamon invoice lookup failed with HTTP status {0}").format(response.status_code)
		)
	try:
		result = response.json()
	except ValueError:
		frappe.throw(_("Pergamon returned a non-JSON invoice lookup response"))
	if not isinstance(result, dict):
		frappe.throw(_("Pergamon returned an unexpected invoice lookup response"))

	# Do not assert reconciliation unless the provider identifies the same
	# originating Sales Invoice and returns an amount in the expected TZS.
	reference = receipt_field(result, "traderInvoiceNo")
	amount = receipt_field(result, "totalAmount")
	expected = flt(doc.get("base_rounded_total") or doc.base_grand_total, 2)
	matches_reference = str(reference or "") == doc.name
	matches_amount = amount is not None and abs(flt(amount, 2) - expected) <= 0.05
	verification_code = get_verification_code(result)
	provider_currency = receipt_field(result, "currency")
	currency_matches = provider_currency == "TZS"
	return {
		"found": True,
		"verified": bool(matches_reference and matches_amount and currency_matches and verification_code),
		"currency_matches": currency_matches,
		"provider_currency": provider_currency,
		"reference_matches": matches_reference,
		"amount_matches": matches_amount,
		"expected_tzs": expected,
		"provider_reference": reference,
		"provider_amount": amount,
		"verification_code": verification_code,
		"verification_url": get_verification_url(result),
		"data": result,
		"message": _("Lookup completed; no Sales Invoice fields were changed"),
	}


def extract_invoice_list(response):
	"""Accept a direct array or a common list envelope; reject unknown schemas."""
	if isinstance(response, list):
		return response
	if not isinstance(response, dict):
		frappe.throw(_("Unexpected Pergamon invoice list response"))
	for key in ("data", "invoices", "results"):
		value = response.get(key)
		if isinstance(value, list):
			return value
		if isinstance(value, dict):
			for nested_key in ("invoices", "items", "results", "data"):
				if isinstance(value.get(nested_key), list):
					return value[nested_key]
	frappe.throw(_("Pergamon invoice list format is not recognized; no reconciliation was performed"))


def compare_pergamon_invoices(records, erpnext_invoices):
	"""Read-only comparison; absence from an unpaginated list is not proof of a missing receipt."""
	index = {row.name: row for row in erpnext_invoices}
	rows = []
	for receipt in records:
		if not isinstance(receipt, dict):
			continue
		reference = receipt_field(receipt, "traderInvoiceNo")
		reference = str(reference or "").strip()
		invoice = index.get(reference)
		provider_amount = receipt_field(receipt, "totalAmount")
		currency = receipt_field(receipt, "currency")
		verification = get_verification_code(receipt)
		expected = (
			flt(invoice.base_rounded_total or invoice.base_grand_total, 2) if invoice else None
		)
		amount_matches = (
			invoice is not None
			and provider_amount is not None
			and abs(flt(provider_amount, 2) - expected) <= 0.05
		)
		rows.append(
			{
				"trader_invoice_no": reference,
				"erpnext_invoice": invoice.name if invoice else None,
				"erpnext_vfd_status": invoice.vfd_status if invoice else None,
				"provider_invoice_id": receipt_field(receipt, "id", "invoiceId"),
				"provider_amount": provider_amount,
				"expected_tzs": expected,
				"currency": currency,
				"verification_code": verification,
				"verification_url": receipt_field(
					receipt, "verificationUrl", "traReceiptVerificationUrl"
				),
				"status": (
					"Verified"
					if invoice and amount_matches and currency == "TZS" and verification
					else "Mismatch" if invoice else "Not linked to accessible Sales Invoice"
				),
			}
		)
	return rows


@frappe.whitelist()
def list_pergamon_invoices(sales_invoice):
	"""Read Pergamon's invoice register and compare returned entries with ERPNext.

	The Postman collection does not specify filters, ordering or pagination.
	No missing-invoice conclusion may be drawn from an incomplete/unknown list.
	"""
	if not sales_invoice:
		frappe.throw(_("Sales Invoice is required to select the company"))
	doc = frappe.get_doc("Sales Invoice", sales_invoice)
	doc.check_permission("read")
	if not set(frappe.get_roles()).intersection({"System Manager", "Accounts Manager", "Sales Manager"}):
		frappe.throw(_("Viewing the Pergamon invoice register requires a manager role"))
	provider = get_provider()
	selected = frappe.db.get_value("Company VFD Provider", doc.company, "vfd_provider")
	if selected != provider.name:
		frappe.throw(_("Pergamon is not the selected VFD provider for this company"))
	if provider.sandbox or not provider.base_url.lower().startswith("https://"):
		frappe.throw(_("Pergamon requires a configured HTTPS production endpoint"))
	endpoint = provider.get_endpoint("get_invoices")
	if endpoint != "/invoices":
		frappe.throw(_("Unexpected Pergamon invoice list endpoint configuration"))
	settings = frappe.get_doc(SETTINGS_DOCTYPE, doc.company)
	try:
		response = requests.get(
			provider.base_url.rstrip("/") + endpoint,
			headers={"Accept": "application/json"},
			auth=(settings.username, settings.get_password("password")),
			timeout=TIMEOUT,
			verify=get_tls_verify(),
		)
	except requests.exceptions.SSLError:
		raise_tls_error()
	except requests.RequestException:
		frappe.throw(_("Pergamon invoice register could not be retrieved"))
	if not response.ok:
		frappe.throw(_("Pergamon invoice register returned HTTP {0}").format(response.status_code))
	try:
		body = response.json()
	except ValueError:
		frappe.throw(_("Pergamon invoice register returned non-JSON content"))
	records = extract_invoice_list(body)
	if len(records) > 2000:
		frappe.throw(_("Pergamon response contains too many invoices for an interactive comparison"))
	references = [
		str(receipt_field(row, "traderInvoiceNo") or "").strip()
		for row in records if isinstance(row, dict)
	]
	references = list({ref for ref in references if ref})
	matched = (
		frappe.get_list(
			"Sales Invoice",
			filters={"company": doc.company, "name": ["in", references]},
			fields=["name", "vfd_status", "base_grand_total", "base_rounded_total"],
			limit_page_length=len(references),
		)
		if references else []
	)
	rows = compare_pergamon_invoices(records, matched)
	return {
		"company": doc.company,
		"count_returned": len(records),
		"matched_count": sum(bool(row["erpnext_invoice"]) for row in rows),
		"rows": rows,
		"complete_register": False,
		"message": _(
			"Only records returned by Pergamon are compared. Pagination and full-register "
			"coverage are not documented; missing ERPNext fiscal receipts cannot yet be inferred."
		),
	}


def get_zreport_totals(body):
	"""Extract report totals only when their schema is recognizable."""
	if not isinstance(body, dict):
		return None, None
	for node in (body.get("data"), body.get("report"), body):
		if not isinstance(node, dict):
			continue
		amount = next(
			(node[k] for k in ("totalAmount", "totalSales", "totalTurnover") if node.get(k) is not None),
			None,
		)
		count = next(
			(node[k] for k in ("receiptCount", "receiptsIssued", "invoiceCount") if node.get(k) is not None),
			None,
		)
		if amount is not None or count is not None:
			return amount, count
	return None, None


@frappe.whitelist()
def fetch_pergamon_zreport(company, report_date):
	"""Retrieve and archive the daily Pergamon Z report, without altering fiscal invoices.

	Pergamon response schema is not documented in the supplied Postman collection.
	The raw response is authoritative; comparisons are explicitly indicative.
	"""
	if not set(frappe.get_roles()).intersection({"System Manager", "Accounts Manager"}):
		frappe.throw(_("Retrieving Pergamon Z Reports requires an authorized manager"))
	frappe.has_permission("Company", "read", doc=company, throw=True)
	report_day = getdate(report_date)
	if str(report_day) != str(report_date or ""):
		frappe.throw(_("Enter a valid Z Report date in YYYY-MM-DD format"))
	provider = get_provider()
	selected = frappe.db.get_value("Company VFD Provider", company, "vfd_provider")
	if selected != provider.name:
		frappe.throw(_("Pergamon is not the selected VFD provider for this company"))
	if provider.sandbox or not provider.base_url.lower().startswith("https://"):
		frappe.throw(_("Pergamon Z Report requires an HTTPS production endpoint"))
	endpoint = provider.get_endpoint("zreports")
	if endpoint != "/zreports":
		frappe.throw(_("Unexpected Pergamon Z Report endpoint configuration"))
	settings = frappe.get_doc(SETTINGS_DOCTYPE, company)
	try:
		response = requests.get(
			provider.base_url.rstrip("/") + endpoint,
			params={"date": str(report_day)},
			headers={"Accept": "application/json"},
			auth=(settings.username, settings.get_password("password")),
			timeout=TIMEOUT,
			verify=get_tls_verify(),
		)
	except requests.exceptions.SSLError:
		raise_tls_error()
	except requests.RequestException:
		frappe.throw(_("Pergamon Z Report retrieval failed. Check connectivity and retry"))
	if not response.ok:
		frappe.throw(_("Pergamon Z Report request returned HTTP {0}").format(response.status_code))
	try:
		body = response.json()
	except ValueError:
		frappe.throw(_("Pergamon returned a non-JSON Z Report response"))
	if not isinstance(body, (dict, list)):
		frappe.throw(_("Pergamon returned an unexpected Z Report response"))
	amount, count = get_zreport_totals(body)
	# Use fiscal submission date; invoice posting_date may differ.
	local = frappe.get_list(
		"Sales Invoice",
		filters={
			"company": company,
			"docstatus": 1,
			"vfd_status": "Success",
			"vfd_date": str(report_day),
		},
		fields=["base_grand_total", "base_rounded_total"],
		limit_page_length=0,
	)
	local_amount = flt(
		sum(flt(row.base_rounded_total or row.base_grand_total, 2) for row in local), 2
	)
	provider_amount = flt(amount, 2) if amount is not None else None
	difference = flt(provider_amount - local_amount, 2) if provider_amount is not None else None
	status = "Pending Schema Confirmation"
	if provider_amount is not None and count is not None:
		status = (
			"Indicative Match"
			if abs(difference) <= 0.05 and int(count) == len(local)
			else "Indicative Difference"
		)
	existing = frappe.get_all(
		"VFD Z Report",
		filters={"company": company, "vfd_provider": provider.name, "report_date": str(report_day)},
		pluck="name",
		limit_page_length=1,
	)
	doc = frappe.get_doc("VFD Z Report", existing[0]) if existing else frappe.new_doc("VFD Z Report")
	doc.company = company
	doc.vfd_provider = provider.name
	doc.report_date = report_day
	doc.fetched_at = now_datetime()
	doc.reconciliation_status = status
	doc.provider_total = provider_amount
	doc.provider_receipt_count = int(count) if count is not None else None
	doc.erpnext_total = local_amount
	doc.erpnext_receipt_count = len(local)
	doc.difference = difference
	doc.raw_response = json.dumps(body, ensure_ascii=False, indent=2)
	doc.save() if existing else doc.insert()
	return {
		"z_report": doc.name,
		"status": status,
		"provider_total": provider_amount,
		"erpnext_total": local_amount,
		"provider_receipt_count": count,
		"erpnext_receipt_count": len(local),
		"difference": difference,
		"message": _(
			"Z Report archived. Reconciliation is indicative until Pergamon's response schema "
			"and report scope are verified."
		),
	}


@frappe.whitelist()
def fetch_pergamon_periodic_report(company, from_date, to_date):
	"""Retrieve and archive a Pergamon period summary without changing fiscal invoices.

	The Postman collection documents from/to parameters but no response schema.
	Only a recognizable summary can be compared, and then indicatively.
	"""
	try:
		from_day, to_day = getdate(from_date), getdate(to_date)
	except (TypeError, ValueError):
		frappe.throw(_("Enter valid report dates in YYYY-MM-DD format"))
	if str(from_day) != str(from_date or "") or str(to_day) != str(to_date or ""):
		frappe.throw(_("Enter valid report dates in YYYY-MM-DD format"))
	if from_day > to_day:
		frappe.throw(_("From Date must not be after To Date"))
	if (to_day - from_day).days > 366:
		frappe.throw(_("Choose a reporting period of no more than 367 days"))
	if not set(frappe.get_roles()).intersection({"System Manager", "Accounts Manager"}):
		frappe.throw(_("Retrieving Pergamon periodic reports requires an authorized manager"))
	frappe.has_permission("Company", "read", doc=company, throw=True)
	provider = get_provider()
	selected = frappe.db.get_value("Company VFD Provider", company, "vfd_provider")
	if selected != provider.name:
		frappe.throw(_("Pergamon is not the selected VFD provider for this company"))
	if provider.sandbox or not provider.base_url.lower().startswith("https://"):
		frappe.throw(_("Pergamon periodic report requires an HTTPS production endpoint"))
	endpoint = provider.get_endpoint("periodic_reports")
	if endpoint != "/periodic-reports":
		frappe.throw(_("Unexpected Pergamon periodic report endpoint configuration"))
	settings = frappe.get_doc(SETTINGS_DOCTYPE, company)
	try:
		response = requests.get(
			provider.base_url.rstrip("/") + endpoint,
			params={"from": str(from_day), "to": str(to_day)},
			headers={"Accept": "application/json"},
			auth=(settings.username, settings.get_password("password")),
			timeout=TIMEOUT,
			verify=get_tls_verify(),
		)
	except requests.exceptions.SSLError:
		raise_tls_error()
	except requests.RequestException:
		frappe.throw(_("Pergamon periodic report retrieval failed. Check connectivity and retry"))
	if not response.ok:
		frappe.throw(_("Pergamon periodic report returned HTTP {0}").format(response.status_code))
	try:
		body = response.json()
	except ValueError:
		frappe.throw(_("Pergamon returned a non-JSON periodic report response"))
	if not isinstance(body, (dict, list)):
		frappe.throw(_("Pergamon returned an unexpected periodic report response"))

	amount, count = get_zreport_totals(body)
	# vfd_date represents the fiscal receipt date, which may differ from posting_date.
	local = frappe.get_list(
		"Sales Invoice",
		filters={
			"company": company,
			"docstatus": 1,
			"vfd_status": "Success",
			"vfd_date": ["between", [str(from_day), str(to_day)]],
		},
		fields=["base_grand_total", "base_rounded_total"],
		limit_page_length=0,
	)
	local_total = flt(
		sum(flt(row.base_rounded_total or row.base_grand_total, 2) for row in local), 2
	)
	provider_total = flt(amount, 2) if amount is not None else None
	difference = flt(provider_total - local_total, 2) if provider_total is not None else None
	status = "Pending Schema Confirmation"
	if provider_total is not None and count is not None:
		status = (
			"Indicative Match"
			if abs(difference) <= 0.05 and int(count) == len(local)
			else "Indicative Difference"
		)

	existing = frappe.get_all(
		"VFD Periodic Report",
		filters={
			"company": company,
			"vfd_provider": provider.name,
			"from_date": str(from_day),
			"to_date": str(to_day),
		},
		pluck="name",
		limit_page_length=1,
	)
	doc = (
		frappe.get_doc("VFD Periodic Report", existing[0])
		if existing
		else frappe.new_doc("VFD Periodic Report")
	)
	doc.company = company
	doc.vfd_provider = provider.name
	doc.from_date = from_day
	doc.to_date = to_day
	doc.fetched_at = now_datetime()
	doc.comparison_status = status
	doc.provider_total = provider_total
	doc.erpnext_total = local_total
	doc.difference = difference
	doc.provider_receipt_count = int(count) if count is not None else None
	doc.erpnext_receipt_count = len(local)
	doc.raw_response = json.dumps(body, ensure_ascii=False, indent=2)
	doc.save() if existing else doc.insert()
	return {
		"periodic_report": doc.name,
		"status": status,
		"provider_total": provider_total,
		"erpnext_total": local_total,
		"difference": difference,
		"provider_receipt_count": count,
		"erpnext_receipt_count": len(local),
		"message": _(
			"Periodic report archived. Comparison remains indicative until Pergamon's "
			"response schema and summary scope have been confirmed."
		),
	}
