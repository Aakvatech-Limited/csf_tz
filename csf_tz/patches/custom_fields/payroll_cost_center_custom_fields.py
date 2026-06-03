from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
	df = {
		"fieldname": "payroll_cost_center",
		"label": "Payroll Cost Center",
		"fieldtype": "Data",
		"insert_after": "payroll_entry",
		"fetch_from": "employee.payroll_cost_center",
	}

	create_custom_field("Salary Slip", df)
