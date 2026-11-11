# Copyright (c) 2022, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from erpnext import get_company_currency
from frappe import _, msgprint
from frappe.query_builder import Criterion
from frappe.utils import getdate, flt, cstr, cint

from csf_tz.csf_tz.report.salary_slip_conditions import get_currency_and_department_conditions

import calendar

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
		msgprint(_("No salary slip found for the previous month: {0} {1}".format(
			frappe.bold(calendar.month_name[prev_month]), frappe.bold(prev_year)))
		)
		return columns, cur_salary_slips
	
	if len(cur_salary_slips) == 0:
		msgprint(_("No salary slip found for the this month: {0} {1}".format(
			frappe.bold(calendar.month_name[getdate(filters.from_date).month]),
			frappe.bold(getdate(filters.from_date).year)))
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
			"options": "Employee"
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"width": 150,
			"options": "Department"
		},
		{
			"fieldname": "prev_gross_pay",
			"label": _("Gross Pay {0}-{1}".format(prev_month_name, prev_year)),
			"fieldtype": "Float",
			"width": 250,
			"precision": 2
		},
		{
			"fieldname": "cur_gross_pay",
			"label": _("Gross Pay {0}-{1}".format(cur_month_name, cur_year)),
			"fieldtype": "Float",
			"width": 250,
			"precision": 2
		},
		{
			"fieldname": "gross_difference_amount",
			"label": _("Gross Difference Amount"),
			"fieldtype": "Data",
			"width": 150
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
			if (
				cur_ss_row.employee == prev_ss_row.employee and
				flt(cur_ss_row.cur_gross_pay, 2) == flt(prev_ss_row.prev_gross_pay, 2)
			):
				unique_prev_employees.append(prev_ss_row.employee)
				unique_cur_employees.append(cur_ss_row.employee)
			
			elif (
				cur_ss_row.employee == prev_ss_row.employee and
				flt(cur_ss_row.cur_gross_pay, 2) != flt(prev_ss_row.prev_gross_pay, 2)
			):
				unique_prev_employees.append(prev_ss_row.employee)
				unique_cur_employees.append(cur_ss_row.employee)

				gross_amount_diff = flt(flt(cur_ss_row.cur_gross_pay) - flt(prev_ss_row.prev_gross_pay), 2)

				cur_ss_row.update({
					"prev_gross_pay": prev_ss_row.prev_gross_pay,
					"cur_gross_pay": cur_ss_row.cur_gross_pay,
					"gross_difference_amount": get_difference_amount_detail(gross_amount_diff)
				})
				data.append(cur_ss_row)

		# Update employee details for the current month if the employee is not in the list of employees for previous month
		if cur_ss_row.employee not in unique_cur_employees:
			unique_cur_employees.append(cur_ss_row.employee)
			cur_ss_row.update({
				"prev_gross_pay": 0,
				"cur_gross_pay": cur_ss_row.cur_gross_pay,
				"gross_difference_amount": "+ " + str(cur_ss_row.cur_gross_pay)
			})

			data.append(cur_ss_row)

	return update_unique_prev_employee_ss_details(data, prev_ss, unique_prev_employees)

def update_unique_prev_employee_ss_details(data, prev_ss, unique_prev_employees):
	""""Updating unique employee details of previous month if the employee is not in the list of employees for the current month"""

	for prev_row in prev_ss:
		if prev_row.employee not in unique_prev_employees:
			unique_prev_employees.append(prev_row.employee)
			prev_row.update({
				"prev_gross_pay": prev_row.prev_gross_pay,
				"cur_gross_pay": 0,
				"gross_difference_amount": "- " + str(prev_row.prev_gross_pay)
			})

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

def get_prev_salary_slips(filters, company_currency, prev_first_date, prev_last_date):
	"""Get submitted salary slips for precious month"""

	custom_filters = filters
	custom_filters.update({
		"prev_first_date": prev_first_date,
		"prev_last_date": prev_last_date
	})
	salary_slip = frappe.qb.DocType("Salary Slip")
	prev_salary_slips = (
		frappe.qb.from_(salary_slip)
		.select(
			salary_slip.name,
			salary_slip.employee,
			salary_slip.employee_name,
			salary_slip.department,
			salary_slip.gross_pay.as_("prev_gross_pay"),
		)
		.where(Criterion.all(get_prev_conditions(salary_slip, custom_filters, company_currency)))
		.orderby(salary_slip.employee)
		.run(as_dict=True)
	)

	return prev_salary_slips or []

def get_cur_salary_slips(filters, company_currency):
	"""Get salary slips for the current month"""

	filters.update({
		"from_date": filters.get("from_date"),
        "to_date": filters.get("to_date")
	})
	salary_slip = frappe.qb.DocType("Salary Slip")
	salary_slips = (
		frappe.qb.from_(salary_slip)
		.select(
			salary_slip.name,
			salary_slip.employee,
			salary_slip.employee_name,
			salary_slip.department,
			salary_slip.gross_pay.as_("cur_gross_pay"),
		)
		.where(Criterion.all(get_cur_conditions(salary_slip, filters, company_currency)))
		.orderby(salary_slip.employee)
		.run(as_dict=True)
	)
	
	return salary_slips or []

def get_prev_month_date(filters):
	"""Get date deatils for previous month"""

	prev_month = getdate(filters.from_date).month - 1
	prev_year = getdate(filters.from_date).year

	if prev_month == 0:
		prev_month = 12
		prev_year = prev_year - 1

	prev_first_date =  getdate(str(prev_year) + "-" + str(prev_month) + "-" + "01")
	prev_last_date = getdate(str(prev_year) + "-" + str(prev_month) + "-" + "{0}".format(
		calendar.monthrange(prev_year, prev_month)[1])
	)

	return prev_first_date, prev_last_date, prev_month, prev_year

def get_prev_conditions(salary_slip, filters, company_currency):
	"""Conditions that will be used to get salary slips for previous month"""
	
	# this is get submitted salary slips for the previous month
	conditions = [salary_slip.docstatus <= 1]

	if filters.get("prev_first_date"):
		conditions.append(salary_slip.start_date >= filters.get("prev_first_date"))
	if filters.get("prev_last_date"):
		conditions.append(salary_slip.end_date <= filters.get("prev_last_date"))

	return conditions + get_common_conditions(salary_slip, filters, company_currency)

def get_cur_conditions(salary_slip, filters, company_currency):
	"""Conditions that will be used to get salary slips for current month"""

	conditions = []
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	if filters.get("docstatus"):
		conditions.append(salary_slip.docstatus == doc_status[filters.get("docstatus")])
	if filters.get("from_date"):
		conditions.append(salary_slip.start_date >= filters.get("from_date"))
	if filters.get("to_date"):
		conditions.append(salary_slip.end_date <= filters.get("to_date"))

	return conditions + get_common_conditions(salary_slip, filters, company_currency)

def get_common_conditions(salary_slip, filters, company_currency):
	"""Company, employee, currency and department conditions shared by both months"""

	conditions = []
	for fieldname in ("company", "employee"):
		if filters.get(fieldname):
			conditions.append(salary_slip[fieldname] == filters.get(fieldname))

	return conditions + get_currency_and_department_conditions(salary_slip, filters, company_currency)
