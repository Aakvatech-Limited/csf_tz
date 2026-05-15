import json

import frappe
from frappe import _
from selcom_apigw_client import apigwClient


def create_order_log(method, status, request_json, response, reference):
	doc = frappe.new_doc("Selcom Order Log")
	doc.date = frappe.utils.today()
	doc.time = frappe.utils.nowtime()
	doc.method = method
	doc.status = status
	doc.reference = reference
	doc.request_data = json.dumps(request_json, indent=4)
	doc.response_data = json.dumps(response, indent=4)
	doc.insert(ignore_permissions=True)


@frappe.whitelist()
def create_order_minimal():
	# Initialize API client
	apiKey = ""
	apiSecret = ""
	baseUrl = "https://apigw.selcommobile.com/v1"

	client = apigwClient.Client(baseUrl, apiKey, apiSecret)

	# Order data
	orderDict = {
		"vendor": "TILL61056542",
		"order_id": "1218d5Qb",
		"buyer_email": "john@example.com",
		"buyer_name": "John Joh",
		"buyer_phone": "255789968024",
		"amount": 8000,
		"currency": "TZS",
		"buyer_remarks": "None",
		"merchant_remarks": "None",
		"no_of_items": 1,
	}

	# API endpoint
	orderPath = "/checkout/create-order-minimal"

	# Send order request
	try:
		response = client.postFunc(orderPath, orderDict)
		if response.get("resultcode") != "000":
			frappe.log_error(
				f"Error on Create Order {response.get('reference')} to Payment Gateway",
				response,
			)
			create_order_log(
				"Create Order Minimal",
				"Failed",
				orderDict,
				response,
				reference=response.get("reference"),
			)
		else:
			frappe.msgprint(_("Order created successfully"), alert=True)
			create_order_log(
				"Create Order Minimal",
				"Success",
				orderDict,
				response,
				reference=response.get("reference"),
			)
		return response

	except Exception as e:
		frappe.log_error(
			f"Error on Create Order {response.get('reference')} to Payment Gateway",
			str(e),
		)
		create_order_log(
			"Create Order Minimal",
			"Failed",
			orderDict,
			str(e),
			reference=response.get("reference"),
		)
		frappe.throw(_("Failed to create order, please try again, or contact the administrator"))
