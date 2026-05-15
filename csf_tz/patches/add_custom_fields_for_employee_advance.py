from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	fields = {
		"Employee Advance": [
			dict(
				fieldname="date_section",
				fieldtype="Section Break",
				label="Date Section",
				insert_after="mode_of_payment",
			),
			dict(
				fieldname="from_date",
				fieldtype="Date",
				label="From Date",
				insert_after="date_section",
			),
			dict(
				fieldname="to_date",
				fieldtype="Date",
				label="To Date",
				insert_after="from_date",
			),
		]
	}
	create_custom_fields(fields, update=True)
