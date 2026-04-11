# Copyright (c) 2026, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def validate_filters(filters):
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required"))

	if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
		frappe.throw(_("From Date cannot be after To Date"))


def get_columns():
	return [
		{"label": _("SN"), "fieldname": "sn", "fieldtype": "Int", "width": 70},
		{
			"label": _("Employee TIN"),
			"fieldname": "employee_tin",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("National Identification Number"),
			"fieldname": "national_identification_number",
			"fieldtype": "Data",
			"width": 210,
		},
		{
			"label": _("Type of Employment"),
			"fieldname": "type_of_employment",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Residential Status"),
			"fieldname": "residential_status",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Social Security Number"),
			"fieldname": "social_security_number",
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"label": _("Employee Location"),
			"fieldname": "employee_location",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Basic Pay"),
			"fieldname": "basic_pay",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Other Allowances"),
			"fieldname": "other_allowances",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Gross Pay"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Deductions"),
			"fieldname": "deductions",
			"fieldtype": "Currency",
			"width": 130,
		},
	]


def get_data(filters):
	salary_slips = get_salary_slips(filters)
	if not salary_slips:
		return []

	slip_names = [d.name for d in salary_slips]
	employee_ids = [d.employee for d in salary_slips if d.employee]

	employee_map = get_employee_map(employee_ids)
	basic_map = get_basic_pay_map(slip_names)

	data = []
	for idx, slip in enumerate(salary_slips, start=1):
		employee_details = employee_map.get(slip.employee, {})
		basic_pay = flt(basic_map.get(slip.name))
		gross_pay = flt(slip.gross_pay)

		data.append(
			{
				"sn": idx,
				"employee_tin": employee_details.get("employee_tin"),
				"employee_name": employee_details.get("employee_name")
				or slip.employee_name,
				"national_identification_number": employee_details.get(
					"national_identification_number"
				),
				"type_of_employment": employee_details.get("type_of_employment"),
				"residential_status": employee_details.get("residential_status"),
				"social_security_number": employee_details.get("social_security_number"),
				"employee_location": employee_details.get("employee_location"),
				"basic_pay": basic_pay,
				"other_allowances": gross_pay - basic_pay,
				"gross_pay": gross_pay,
				"deductions": flt(slip.total_deduction),
			}
		)

	return data


def get_salary_slips(filters):
	return frappe.get_all(
		"Salary Slip",
		filters={
			"docstatus": 1,
			"start_date": [">=", filters.get("from_date")],
			"end_date": ["<=", filters.get("to_date")],
		},
		fields=["name", "employee", "employee_name", "gross_pay", "total_deduction"],
		order_by="employee_name asc, start_date asc",
		limit_page_length=0,
	)


def get_basic_pay_map(slip_names):
	if not slip_names:
		return {}

	basic_rows = frappe.get_all(
		"Salary Detail",
		filters={
			"parent": ["in", slip_names],
			"parenttype": "Salary Slip",
			"parentfield": "earnings",
			"salary_component": "Basic",
		},
		fields=["parent", "amount"],
		limit_page_length=0,
	)

	basic_map = {}
	for row in basic_rows:
		basic_map[row.parent] = flt(basic_map.get(row.parent)) + flt(row.amount)

	return basic_map


def get_employee_map(employee_ids):
	if not employee_ids:
		return {}

	meta = frappe.get_meta("Employee")
	field_selector = {
		"employee_tin": get_existing_field(meta, ["tin_number"]),
		"employee_name": get_existing_field(meta, ["employee_name"]),
		"national_identification_number": get_existing_field(meta, ["national_identity"]),
		"type_of_employment": get_existing_field(meta, ["employment_type"]),
		"residential_status": get_existing_field(meta, ["residential_status"]),
		"social_security_number": get_existing_field(meta, ["pension_fund_number"]),
		"employee_location": get_existing_field(meta, ["employee_location"]),
	}

	fields = ["name"]
	for fieldname in field_selector.values():
		if fieldname and fieldname not in fields:
			fields.append(fieldname)

	employees = frappe.get_all(
		"Employee",
		filters={"name": ["in", employee_ids]},
		fields=fields,
		limit_page_length=0,
	)

	employee_map = {}
	for row in employees:
		employee_map[row.name] = {}
		for output_field, source_field in field_selector.items():
			employee_map[row.name][output_field] = row.get(source_field) if source_field else ""

	return employee_map


def get_existing_field(meta, candidates):
	for fieldname in candidates:
		if meta.has_field(fieldname):
			return fieldname

	return None
