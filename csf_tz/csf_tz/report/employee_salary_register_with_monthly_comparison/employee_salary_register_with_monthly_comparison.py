# Copyright (c) 2022, Aakvatech and contributors
# For license information, please see license.txt

import calendar

import frappe
from erpnext import get_company_currency
from frappe import _, msgprint
from frappe.utils import cstr, flt, getdate
from frappe.utils.nestedset import get_descendants_of


def execute(filters):
	company_currency = get_company_currency(filters.get("company"))

	prev_first_date, prev_last_date, prev_month, prev_year = get_prev_month_date(filters)
	cur_month_name = calendar.month_name[getdate(filters.from_date).month]
	cur_year = getdate(filters.from_date).year

	prev_month_name = calendar.month_name[prev_month]
	columns = get_columns(prev_month_name, cur_month_name, prev_year, cur_year)

	prev_salary_slips = get_prev_salary_slips(filters, company_currency, prev_first_date, prev_last_date)
	cur_salary_slips = get_cur_salary_slips(filters, company_currency)

	if len(prev_salary_slips) == 0:
		msgprint(
			_(
				f"No salary slip found for the previous month: {frappe.bold(calendar.month_name[prev_month])} {frappe.bold(prev_year)}"
			)
		)
		return columns, cur_salary_slips

	if len(cur_salary_slips) == 0:
		msgprint(
			_(
				f"No salary slip found for the this month: {frappe.bold(calendar.month_name[getdate(filters.from_date).month])} {frappe.bold(getdate(filters.from_date).year)}"
			)
		)
		return columns, prev_salary_slips

	data = get_data(prev_salary_slips, cur_salary_slips)

	return columns, data


def get_columns(prev_month_name, cur_month_name, prev_year, cur_year):
	columns = [
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"width": 150,
			"options": "Employee",
		},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 150},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"width": 150,
			"options": "Department",
		},
		{
			"fieldname": "prev_gross_pay",
			"label": _(f"Gross Pay {prev_month_name}-{prev_year}"),
			"fieldtype": "Float",
			"width": 250,
			"precision": 2,
		},
		{
			"fieldname": "cur_gross_pay",
			"label": _(f"Gross Pay {cur_month_name}-{cur_year}"),
			"fieldtype": "Float",
			"width": 250,
			"precision": 2,
		},
		{
			"fieldname": "gross_difference_amount",
			"label": _("Gross Difference Amount"),
			"fieldtype": "Data",
			"width": 150,
		},
	]
	return columns


def get_data(prev_ss, cur_ss):
	"""Merge employee details from current and previous months"""

	data = []
	unique_cur_employees = []
	unique_prev_employees = []

	for cur_ss_row in cur_ss:
		for prev_ss_row in prev_ss:
			if cur_ss_row.employee == prev_ss_row.employee and flt(cur_ss_row.cur_gross_pay, 2) == flt(
				prev_ss_row.prev_gross_pay, 2
			):
				unique_prev_employees.append(prev_ss_row.employee)
				unique_cur_employees.append(cur_ss_row.employee)

			elif cur_ss_row.employee == prev_ss_row.employee and flt(cur_ss_row.cur_gross_pay, 2) != flt(
				prev_ss_row.prev_gross_pay, 2
			):
				unique_prev_employees.append(prev_ss_row.employee)
				unique_cur_employees.append(cur_ss_row.employee)

				gross_amount_diff = flt(flt(cur_ss_row.cur_gross_pay) - flt(prev_ss_row.prev_gross_pay), 2)

				cur_ss_row.update(
					{
						"prev_gross_pay": prev_ss_row.prev_gross_pay,
						"cur_gross_pay": cur_ss_row.cur_gross_pay,
						"gross_difference_amount": get_difference_amount_detail(gross_amount_diff),
					}
				)
				data.append(cur_ss_row)

		# Update employee details for the current month if the employee is not in the list of employees for previous month
		if cur_ss_row.employee not in unique_cur_employees:
			unique_cur_employees.append(cur_ss_row.employee)
			cur_ss_row.update(
				{
					"prev_gross_pay": 0,
					"cur_gross_pay": cur_ss_row.cur_gross_pay,
					"gross_difference_amount": "+ " + str(cur_ss_row.cur_gross_pay),
				}
			)

			data.append(cur_ss_row)

	return update_unique_prev_employee_ss_details(data, prev_ss, unique_prev_employees)


def update_unique_prev_employee_ss_details(data, prev_ss, unique_prev_employees):
	""" "Updating unique employee details of previous month if the employee is not in the list of employees for the current month"""

	for prev_row in prev_ss:
		if prev_row.employee not in unique_prev_employees:
			unique_prev_employees.append(prev_row.employee)
			prev_row.update(
				{
					"prev_gross_pay": prev_row.prev_gross_pay,
					"cur_gross_pay": 0,
					"gross_difference_amount": "- " + str(prev_row.prev_gross_pay),
				}
			)

			data.append(prev_row)
	return data


def get_difference_amount_detail(bsc_amount_diff):
	"""Show + or - sign on the amount difference between current and previous month"""

	result = ""
	if bsc_amount_diff > 0:
		result = "+" + cstr(bsc_amount_diff)
	elif bsc_amount_diff < 0:
		result = "-" + cstr(abs(bsc_amount_diff))
	else:
		result = "0"
	return result


def _salary_filters(filters, company_currency):
	"""Build Frappe filters without interpolating department names into SQL."""
	out = {}
	for key in ("company", "employee"):
		if filters.get(key):
			out[key] = filters[key]
	if filters.get("currency") and filters["currency"] != company_currency:
		out["currency"] = filters["currency"]
	if filters.get("department") and filters.get("company"):
		out["department"] = ["in", get_departments(filters["department"], filters["company"])]
	return out


def get_prev_salary_slips(filters, company_currency, prev_first_date, prev_last_date):
	query_filters = _salary_filters(filters, company_currency)
	query_filters.update(
		{
			"docstatus": ["<=", 1],
			"start_date": [">=", prev_first_date],
			"end_date": ["<=", prev_last_date],
		}
	)
	rows = frappe.get_all(
		"Salary Slip",
		filters=query_filters,
		fields=["name", "employee", "employee_name", "department", "gross_pay"],
		order_by="employee",
	)
	for row in rows:
		row.prev_gross_pay = row.pop("gross_pay")
	return rows


def get_cur_salary_slips(filters, company_currency):
	query_filters = _salary_filters(filters, company_currency)
	if filters.get("from_date"):
		query_filters["start_date"] = [">=", filters["from_date"]]
	if filters.get("to_date"):
		query_filters["end_date"] = ["<=", filters["to_date"]]
	if filters.get("docstatus") not in (None, ""):
		status_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
		status = status_map.get(filters["docstatus"], filters["docstatus"])
		if str(status) not in {"0", "1", "2"}:
			frappe.throw(_("Invalid Salary Slip document status"))
		query_filters["docstatus"] = int(status)
	rows = frappe.get_all(
		"Salary Slip",
		filters=query_filters,
		fields=["name", "employee", "employee_name", "department", "gross_pay"],
		order_by="employee",
	)
	for row in rows:
		row.cur_gross_pay = row.pop("gross_pay")
	return rows


def get_prev_month_date(filters):
	"""Get date deatils for previous month"""

	prev_month = getdate(filters.from_date).month - 1
	prev_year = getdate(filters.from_date).year

	if prev_month == 0:
		prev_month = 12
		prev_year = prev_year - 1

	prev_first_date = getdate(str(prev_year) + "-" + str(prev_month) + "-" + "01")
	prev_last_date = getdate(
		str(prev_year) + "-" + str(prev_month) + "-" + f"{calendar.monthrange(prev_year, prev_month)[1]}"
	)

	return prev_first_date, prev_last_date, prev_month, prev_year


def get_departments(department, company):
	departments_list = get_descendants_of("Department", department)
	departments_list.append(department)
	return departments_list
