import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	fields = {
		"Payroll Entry": [
			{
				"fieldname": "has_payroll_approval",
				"label": "Has Payroll Approval",
				"fieldtype": "Check",
				"insert_after": "exchange_rate",
				"read_only": 1,
			},
		],
		"Salary Slip": [
			{
				"fieldname": "has_payroll_approval",
				"label": "Has Payroll Approval",
				"fieldtype": "Check",
				"insert_after": "letter_head",
				"read_only": 1,
			},
		],
	}

	fields = {doctype: values for doctype, values in fields.items() if frappe.db.exists("DocType", doctype)}
	if not fields:
		return

	create_custom_fields(fields, update=True)
