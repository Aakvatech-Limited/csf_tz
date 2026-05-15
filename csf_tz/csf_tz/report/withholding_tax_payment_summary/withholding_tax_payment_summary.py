# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	rental = filters.get("rental")
	columns, data = get_columns(rental), []

	sales_invoice_data = frappe.get_list("Sales Invoice", filters={"lease_item": rental}, fields=["*"])
	for i in sales_invoice_data:
		tin_number = frappe.get_value("Customer", i.customer, "tax_id")
		lease = frappe.get_value("Lease", i.lease, "property")
		data.append(
			{
				"date": i.posting_date,
				"particulars": i.customer,
				"voucher_ref": i.name,
				"office_no" if rental == "Commercial Rent" else "apt": lease,
				"period": str(i.from_date) + " to " + str(i.to_date) if i.from_date and i.to_date else "",
				"rental_income": "$ " + str(i.total),
				"withholding_tax_usd": "$ " + str(i.total / 10),
				"withholding_tax_tzs": i.base_total / 10,
				"control_sheet_no": i.tra_control_number or "",
				"tax_certificate": i.witholding_tax_certificate_number,
				"tin_number": tin_number or "",
			}
		)
	return columns, data


def get_columns(rental):
	return [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 150},
		{
			"fieldname": "particulars",
			"label": _("Particulars"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 300,
		},
		{"fieldname": "voucher_ref", "label": _("Voucher Ref."), "fieldtype": "Data", "width": 180},
		{
			"fieldname": "office_no" if rental == "Commercial Rent" else "apt",
			"label": _("Shop/Office No") if rental == "Commercial Rent" else "APT",
			"fieldtype": "Data",
			"width": 200,
		},
		{"fieldname": "period", "label": _("Period"), "fieldtype": "Data", "width": 220},
		{
			"fieldname": "rental_income",
			"label": _("Rental Income"),
			"fieldtype": "Data",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "withholding_tax_usd",
			"label": _("Withholding Tax USD"),
			"fieldtype": "Data",
			"options": "currency",
			"width": 180,
		},
		{
			"fieldname": "withholding_tax_tzs",
			"label": _("Withholding Tax TZS"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 180,
		},
		{"fieldname": "control_sheet_no", "label": _("Control Sheet No"), "fieldtype": "Data", "width": 120},
		{
			"fieldname": "tax_certificate",
			"label": _("Withholding Tax Certificate Number"),
			"fieldtype": "Data",
			"width": 250,
		},
		{"fieldname": "tin_number", "label": _("Tin Number"), "fieldtype": "Data", "width": 300},
	]
