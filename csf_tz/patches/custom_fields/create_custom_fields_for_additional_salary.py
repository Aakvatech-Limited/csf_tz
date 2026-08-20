import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	fields = {
		"Additional Salary": [
			{
				"fetch_from": "salary_component.based_on_hourly_rate",
				"fieldname": "based_on_hourly_rate",
				"fieldtype": "Check",
				"insert_after": "type",
				"label": "Based on Hourly Rate",
				"read_only": 1,
			},
			{
				"depends_on": "eval:doc.based_on_hourly_rate==1",
				"fetch_from": "salary_component.hourly_rate",
				"fieldname": "hourly_rate",
				"fieldtype": "Percent",
				"insert_after": "based_on_hourly_rate",
				"label": "Hourly Rate",
				"read_only": 1,
			},
			{
				"depends_on": "hourly_rate",
				"fieldname": "no_of_hours",
				"fieldtype": "Float",
				"insert_after": "hourly_rate",
				"label": "No of Hours",
			},
			{
				"fieldname": "auto_repeat_details",
				"fieldtype": "Section Break",
				"insert_after": "no_of_hours",
				"label": "Auto Repeat Details",
			},
			{
				"allow_on_submit": 1,
				"fieldname": "auto_repeat_frequency",
				"fieldtype": "Select",
				"insert_after": "auto_repeat_details",
				"label": "Auto Repeat Frequency",
				"options": "None\nWeekly\nMonthly\nAnnually",
				"translatable": 1,
			},
			{
				"fieldname": "column_break_15",
				"fieldtype": "Column Break",
				"insert_after": "auto_repeat_frequency",
			},
			{
				"allow_on_submit": 1,
				"fieldname": "auto_repeat_end_date",
				"fieldtype": "Date",
				"insert_after": "column_break_15",
				"label": "Auto Repeat End Date",
			},
			{
				"fieldname": "last_transaction_details",
				"fieldtype": "Section Break",
				"insert_after": "auto_repeat_end_date",
				"label": "Last Transaction Details",
			},
			{
				"allow_on_submit": 1,
				"fieldname": "last_transaction_amount",
				"fieldtype": "Currency",
				"insert_after": "last_transaction_details",
				"label": "Last Transaction Amount",
				"read_only": 1,
			},
			{
				"fieldname": "column_break_19",
				"fieldtype": "Column Break",
				"insert_after": "last_transaction_amount",
			},
			{
				"allow_on_submit": 1,
				"fieldname": "last_transaction_date",
				"fieldtype": "Date",
				"insert_after": "column_break_19",
				"label": "Last Transaction Date",
				"read_only": 1,
			},
			{
				"fieldname": "section_break_17",
				"fieldtype": "Section Break",
				"insert_after": "last_transaction_date",
			},
			{
				"fieldname": "auto_created_based_on",
				"fieldtype": "Link",
				"insert_after": "section_break_17",
				"label": "Auto created based on",
				"options": "Additional Salary",
				"read_only": 1,
			},
		]
	}

	fields = {doctype: values for doctype, values in fields.items() if frappe.db.exists("DocType", doctype)}
	if not fields:
		return

	create_custom_fields(fields, update=True)
