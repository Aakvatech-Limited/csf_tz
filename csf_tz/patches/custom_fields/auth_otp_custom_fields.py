from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	fields = {
		"Customer": [
			{
				"fieldname": "is_authotp_applied",
				"fieldtype": "Check",
				"insert_after": "customer_group",
				"label": "Is AuthOTP Applied",
			},
			{
				"fieldname": "default_authotp_method",
				"fieldtype": "Link",
				"insert_after": "is_authotp_applied",
				"label": "Default AuthOTP Method",
				"options": "OTP Register",
			},
			{
				"fieldname": "authotp_validated",
				"fieldtype": "Check",
				"insert_after": "default_authotp_method",
				"label": "AuthOTP Validated",
			},
		],
		"Sales Invoice": [
			{
				"fieldname": "authotp",
				"fieldtype": "Section Break",
				"insert_after": "amended_from",
				"label": "AuthOTP",
			},
			{
				"fieldname": "authotp_method",
				"fieldtype": "Link",
				"insert_after": "authotp",
				"options": "OTP Register",
				"label": "AuthOTP Method",
			},
			{
				"fieldname": "column_break_sn02w",
				"fieldtype": "Column Break",
				"insert_after": "authotp_method",
			},
			{
				"label": "AuthOTP Validated",
				"fieldname": "authotp_validated",
				"insert_after": "column_break_sn02w",
				"fieldtype": "Check",
				"read_only": 1,
			},
		],
	}
	create_custom_fields(fields, update=True)
