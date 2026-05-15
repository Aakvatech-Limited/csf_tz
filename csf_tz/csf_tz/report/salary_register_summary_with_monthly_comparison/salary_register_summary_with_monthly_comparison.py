import calendar

import erpnext
import frappe
from frappe import _, msgprint
from frappe.query_builder import DocType, Order
from frappe.query_builder import functions as fn
from frappe.utils import cstr, flt, getdate
from frappe.utils.nestedset import get_descendants_of

ss = DocType("Salary Slip")
sd = DocType("Salary Detail")


def execute(filters=None):
	company_currency = erpnext.get_company_currency(filters.get("company"))

	prev_first_date, prev_last_date, prev_month, prev_year = get_prev_month_date(filters)

	prev_salary_slips = get_prev_salary_slips(filters, company_currency, prev_first_date, prev_last_date)
	if len(prev_salary_slips) == 0:
		msgprint(
			_("No salary slip found for the previous month: {0} {1}").format(
				frappe.bold(calendar.month_name[prev_month]), frappe.bold(prev_year)
			)
		)
		return []

	columns = get_columns(filters, prev_month, prev_year)
	data = get_data(filters, company_currency, prev_salary_slips)

	return columns, data


def get_columns(filters, prev_month, prev_year):
	cur_month_name = calendar.month_name[getdate(filters.from_date).month]
	cur_year = getdate(filters.from_date).year

	prev_month_name = calendar.month_name[prev_month]

	columns = []

	if filters.get("based_on_department") == 1:
		columns.append(
			{
				"fieldname": "department",
				"label": _("Department"),
				"fieldtype": "Data",
				"width": 150,
			}
		)

	if filters.get("based_on_cost_center") == 1:
		columns.append(
			{
				"fieldname": "payroll_cost_center",
				"label": _("Cost Center"),
				"fieldtype": "Data",
				"width": 150,
			}
		)

	columns += [
		{
			"fieldname": "salary_component",
			"label": _("Salary Component"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "total_prev_month",
			"label": "{0} {1}".format(prev_month_name, prev_year),
			"fieldtype": "Float",
			"width": 150,
			"precision": 2,
		},
		{
			"fieldname": "total_cur_month",
			"label": "{0} {1}".format(cur_month_name, cur_year),
			"fieldtype": "Float",
			"width": 150,
			"precision": 2,
		},
		{
			"fieldname": "difference_amount",
			"label": _("Difference Amount"),
			"fieldtype": "Data",
			"width": 150,
		},
	]
	return columns


def get_data(filters, company_currency, prev_salary_slips):
	records = []
	if filters.get("currency"):
		filters.get("currency")

	cur_salary_slips = get_cur_salary_slips(filters, company_currency)
	if len(cur_salary_slips) == 0:
		msgprint(
			_("No salary slip found for the this month: {0} {1}").format(
				frappe.bold(calendar.month_name[getdate(filters.from_date).month]),
				frappe.bold(getdate(filters.from_date).year),
			)
		)
		return []

	no_employee_diff = len(cur_salary_slips) - len(prev_salary_slips)
	result = None
	if no_employee_diff > 0:
		result = "+" + cstr(no_employee_diff)
	elif no_employee_diff < 0:
		result = "-" + cstr(abs(no_employee_diff))
	else:
		result = "0"

	records.append(
		{
			"salary_component": "TOTAL EMPLOYEES",
			"total_prev_month": len(prev_salary_slips),
			"total_cur_month": len(cur_salary_slips),
			"difference_amount": result,
		}
	)
	records.append(
		{
			"salary_component": "",
			"total_prev_month": "",
			"total_cur_month": "",
			"difference_amount": "",
		}
	)
	records.append(
		{
			"salary_component": "",
			"total_prev_month": "",
			"total_cur_month": "",
			"difference_amount": "",
		}
	)

	prev_ss_basic = get_prev_ss_basic_map(filters, prev_salary_slips)
	prev_ss_earnings = get_prev_ss_earn_map(filters, prev_salary_slips)
	prev_ss_deductions = get_prev_ss_ded_map(filters, prev_salary_slips)

	basic_data, total_prev_basic, total_cur_basic = get_basic_data(
		filters, records, cur_salary_slips, prev_ss_basic
	)
	basic_data.append(
		{
			"salary_component": "",
			"total_prev_month": "",
			"total_cur_month": "",
			"difference_amount": "",
		}
	)
	basic_data.append(
		{
			"salary_component": "",
			"total_prev_month": "",
			"total_cur_month": "",
			"difference_amount": "",
		}
	)
	earnings_data, total_prev_earning, total_cur_earning = get_earnings_data(
		filters, basic_data, cur_salary_slips, prev_ss_earnings
	)

	cur_gross_pay = total_cur_earning + total_cur_basic
	prev_gross_pay = total_prev_earning + total_prev_basic

	total_gross_amount_diff = flt(cur_gross_pay - prev_gross_pay, 2)
	grs_diff = ""
	if total_gross_amount_diff > 0:
		grs_diff = "+" + cstr(total_gross_amount_diff)
	elif total_gross_amount_diff < 0:
		grs_diff = "-" + cstr(abs(total_gross_amount_diff))
	else:
		grs_diff = "0"

	earnings_data.append(
		{
			"salary_component": "GROSS PAY",
			"total_prev_month": prev_gross_pay,
			"total_cur_month": cur_gross_pay,
			"difference_amount": grs_diff,
		}
	)

	earnings_data.append(
		{
			"salary_component": "",
			"total_prev_month": "",
			"total_cur_month": "",
			"difference_amount": "",
		}
	)
	earnings_data.append(
		{
			"salary_component": "",
			"total_prev_month": "",
			"total_cur_month": "",
			"difference_amount": "",
		}
	)

	data = get_deduction_data(
		filters,
		earnings_data,
		cur_salary_slips,
		prev_ss_deductions,
		cur_gross_pay,
		prev_gross_pay,
	)

	return data


def get_basic_data(filters, data, salary_slips, prev_ss_basic):
	ss_basic_map = get_cur_ss_basic_map(filters, salary_slips)

	total_cur_basic = 0
	unique_cur_basic_salary_components = []
	unique_prev_basic_salary_components = []
	total_prev_basic = sum(flt(d.total_prev_month) for d in prev_ss_basic)
	department_or_cost_center = ""
	if filters.get("based_on_department") == 1:
		department_or_cost_center = "department"
	elif filters.get("based_on_cost_center") == 1:
		department_or_cost_center = "payroll_cost_center"

	for cur_basic_row in ss_basic_map:
		total_cur_basic += cur_basic_row["total_cur_month"]

		for prev_basic_row in prev_ss_basic:
			if cur_basic_row.get(department_or_cost_center) == prev_basic_row.get(
				department_or_cost_center
			) and cur_basic_row.get("salary_component") == prev_basic_row.get("salary_component"):
				bsc_amount_diff = flt(
					cur_basic_row.get("total_cur_month") - prev_basic_row.get("total_prev_month"),
					2,
				)
				result = ""
				if bsc_amount_diff > 0:
					result = "+" + cstr(bsc_amount_diff)
				elif bsc_amount_diff < 0:
					result = "-" + cstr(abs(bsc_amount_diff))
				else:
					result = "0"
				cur_basic_row.update(
					{
						"total_prev_month": prev_basic_row.get("total_prev_month"),
						"difference_amount": result,
					}
				)
				data.append(cur_basic_row)

				unique_cur_basic_salary_components.append(
					{
						department_or_cost_center: cur_basic_row.get(department_or_cost_center),
						"salary_component": cur_basic_row.get("salary_component"),
					}
				)
				unique_prev_basic_salary_components.append(
					{
						department_or_cost_center: prev_basic_row.get(department_or_cost_center),
						"salary_component": prev_basic_row.get("salary_component"),
					}
				)

		cur_row = {
			department_or_cost_center: cur_basic_row.get(department_or_cost_center),
			"salary_component": cur_basic_row.get("salary_component"),
		}
		if cur_row not in unique_cur_basic_salary_components:
			unique_cur_basic_salary_components.append(cur_row)

			data.append(
				{
					department_or_cost_center: cur_basic_row.get(department_or_cost_center),
					"salary_component": cur_basic_row.get("salary_component"),
					"total_prev_month": 0,
					"total_cur_month": cur_basic_row.get("total_cur_month"),
					"difference_amount": "+" + cstr(cur_basic_row.get("total_cur_month")),
				}
			)

	for row in prev_ss_basic:
		prev_row = {
			department_or_cost_center: row.get(department_or_cost_center),
			"salary_component": row.get("salary_component"),
		}
		if prev_row not in unique_prev_basic_salary_components:
			unique_prev_basic_salary_components.append(prev_row)
			data.append(
				{
					department_or_cost_center: row.get(department_or_cost_center),
					"salary_component": row.get("salary_component"),
					"total_prev_month": row.get("total_prev_month") or 0,
					"total_cur_month": 0,
					"difference_amount": "-" + cstr(row.get("total_prev_month")),
				}
			)

	total_bsc_amount_diff = flt(total_cur_basic - total_prev_basic, 2)
	d = ""
	if total_bsc_amount_diff > 0:
		d = "+" + cstr(total_bsc_amount_diff)
	elif total_bsc_amount_diff < 0:
		d = "-" + cstr(abs(total_bsc_amount_diff))
	else:
		d = "0"

	data.append(
		{
			department_or_cost_center: "",
			"salary_component": "Total Basic",
			"total_prev_month": total_prev_basic,
			"total_cur_month": total_cur_basic,
			"difference_amount": d,
		}
	)

	return data, total_prev_basic, total_cur_basic


def get_earnings_data(filters, data, cur_salary_slips, prev_ss_earnings):
	ss_earning_map = get_cur_ss_earning_map(filters, cur_salary_slips)

	total_cur_earning = 0
	unique_cur_earnings_salary_components = []
	unique_prev_earnings_salary_components = []
	total_prev_earning = sum(flt(d.total_prev_month) for d in prev_ss_earnings)
	department_or_cost_center = ""
	if filters.get("based_on_department") == 1:
		department_or_cost_center = "department"
	elif filters.get("based_on_cost_center") == 1:
		department_or_cost_center = "payroll_cost_center"

	for cur_earning_row in ss_earning_map:
		total_cur_earning += cur_earning_row["total_cur_month"]

		for prev_earning_row in prev_ss_earnings:
			if cur_earning_row.get(department_or_cost_center) == prev_earning_row.get(
				department_or_cost_center
			) and cur_earning_row.get("salary_component") == prev_earning_row.get("salary_component"):
				earn_amount_diff = flt(
					cur_earning_row.get("total_cur_month") - prev_earning_row.get("total_prev_month"),
					2,
				)
				result = ""
				if earn_amount_diff > 0:
					result = "+" + cstr(earn_amount_diff)
				elif earn_amount_diff < 0:
					result = "-" + cstr(abs(earn_amount_diff))
				else:
					result = "0"

				cur_earning_row.update(
					{
						"total_prev_month": prev_earning_row.get("total_prev_month"),
						"difference_amount": result,
					}
				)
				data.append(cur_earning_row)

				unique_cur_earnings_salary_components.append(
					{
						department_or_cost_center: cur_earning_row.get(department_or_cost_center),
						"salary_component": cur_earning_row.get("salary_component"),
					}
				)
				unique_prev_earnings_salary_components.append(
					{
						department_or_cost_center: prev_earning_row.get(department_or_cost_center),
						"salary_component": prev_earning_row.get("salary_component"),
					}
				)

		cur_row = {
			department_or_cost_center: cur_earning_row.get(department_or_cost_center),
			"salary_component": cur_earning_row.get("salary_component"),
		}
		if cur_row not in unique_cur_earnings_salary_components:
			unique_cur_earnings_salary_components.append(cur_row)

			data.append(
				{
					department_or_cost_center: cur_earning_row.get(department_or_cost_center),
					"salary_component": cur_earning_row.get("salary_component"),
					"total_prev_month": 0,
					"total_cur_month": cur_earning_row.get("total_cur_month"),
					"difference_amount": "+" + cstr(cur_earning_row.get("total_cur_month")),
				}
			)

	for row in prev_ss_earnings:
		prev_row = {
			department_or_cost_center: row.get(department_or_cost_center),
			"salary_component": row.get("salary_component"),
		}
		if prev_row not in unique_prev_earnings_salary_components:
			unique_prev_earnings_salary_components.append(prev_row)
			data.append(
				{
					department_or_cost_center: row.get(department_or_cost_center),
					"salary_component": row.get("salary_component"),
					"total_prev_month": row.get("total_prev_month") or 0,
					"total_cur_month": 0,
					"difference_amount": "-" + cstr(row.get("total_prev_month")),
				}
			)
	total_earn_amount_diff = flt(total_cur_earning - total_prev_earning, 2)
	d = ""
	if total_earn_amount_diff > 0:
		d = "+" + cstr(total_earn_amount_diff)
	elif total_earn_amount_diff < 0:
		d = "-" + cstr(abs(total_earn_amount_diff))
	else:
		d = "0"

	data.append(
		{
			department_or_cost_center: "",
			"salary_component": "TOTAL ALLOWANCES",
			"total_prev_month": total_prev_earning,
			"total_cur_month": total_cur_earning,
			"difference_amount": d,
		}
	)

	return data, total_prev_earning, total_cur_earning


def get_deduction_data(
	filters,
	data,
	salary_slips,
	prev_ss_deductions,
	cur_gross_pay,
	prev_gross_pay,
):
	ss_deduction_map = get_cur_ss_ded_map(filters, salary_slips)

	total_cur_deduction = 0
	unique_cur_deduction_salary_components = []
	unique_prev_deduction_salary_components = []
	total_prev_deduction = sum(flt(d.total_prev_month) for d in prev_ss_deductions)
	department_or_cost_center = ""
	if filters.get("based_on_department") == 1:
		department_or_cost_center = "department"
	elif filters.get("based_on_cost_center") == 1:
		department_or_cost_center = "payroll_cost_center"

	for cur_deduction_row in ss_deduction_map:
		total_cur_deduction += cur_deduction_row["total_cur_month"]

		for prev_deduction_row in prev_ss_deductions:
			if cur_deduction_row.get("salary_component") == prev_deduction_row.get(
				"salary_component"
			) and cur_deduction_row.get(department_or_cost_center) == prev_deduction_row.get(
				department_or_cost_center
			):
				ded_amount_diff = flt(
					cur_deduction_row.get("total_cur_month") - prev_deduction_row.get("total_prev_month"),
					2,
				)
				result = ""
				if ded_amount_diff > 0:
					result = "+" + cstr(ded_amount_diff)
				elif ded_amount_diff < 0:
					result = "-" + cstr(abs(ded_amount_diff))
				else:
					result = "0"

				cur_deduction_row.update(
					{
						"total_prev_month": prev_deduction_row.get("total_prev_month"),
						"difference_amount": result,
					}
				)
				data.append(cur_deduction_row)

				unique_cur_deduction_salary_components.append(
					{
						department_or_cost_center: cur_deduction_row.get(department_or_cost_center),
						"salary_component": cur_deduction_row.get("salary_component"),
					}
				)

				unique_prev_deduction_salary_components.append(
					{
						department_or_cost_center: prev_deduction_row.get(department_or_cost_center),
						"salary_component": prev_deduction_row.get("salary_component"),
					}
				)

		cur_row = {
			"salary_component": cur_deduction_row.get("salary_component"),
			department_or_cost_center: cur_deduction_row.get(department_or_cost_center),
		}
		if cur_row not in unique_cur_deduction_salary_components:
			unique_cur_deduction_salary_components.append(cur_row)

			data.append(
				{
					department_or_cost_center: cur_deduction_row.get(department_or_cost_center),
					"salary_component": cur_deduction_row.get("salary_component"),
					"total_prev_month": 0,
					"total_cur_month": cur_deduction_row.get("total_cur_month"),
					"difference_amount": "+" + cstr(cur_deduction_row.get("total_cur_month")),
				}
			)

	for row in prev_ss_deductions:
		prev_row = {
			department_or_cost_center: row.get(department_or_cost_center),
			"salary_component": row.get("salary_component"),
		}
		if prev_row not in unique_prev_deduction_salary_components:
			unique_prev_deduction_salary_components.append(prev_row)
			data.append(
				{
					department_or_cost_center: row.get(department_or_cost_center),
					"salary_component": row.get("salary_component"),
					"total_prev_month": row.get("total_prev_month"),
					"total_cur_month": 0,
					"difference_amount": "-" + cstr(row.get("total_prev_month")),
				}
			)
	total_ded_amount_diff = flt(total_cur_deduction - total_prev_deduction, 2)
	d = ""
	if total_ded_amount_diff > 0:
		d = "+" + cstr(total_ded_amount_diff)
	elif total_ded_amount_diff < 0:
		d = "-" + cstr(abs(total_ded_amount_diff))
	else:
		d = "0"

	data.append(
		{
			department_or_cost_center: "",
			"salary_component": "TOTAL DEDUCTIONS",
			"total_prev_month": total_prev_deduction,
			"total_cur_month": total_cur_deduction,
			"difference_amount": d,
		}
	)

	net_pay_amount_diff = flt(
		(cur_gross_pay - total_cur_deduction) - (prev_gross_pay - total_prev_deduction),
		2,
	)
	h = ""
	if net_pay_amount_diff > 0:
		h = "+" + cstr(net_pay_amount_diff)
	elif net_pay_amount_diff < 0:
		h = "-" + cstr(abs(net_pay_amount_diff))
	else:
		h = "0"

	data.append(
		{
			department_or_cost_center: "",
			"salary_component": "NET PAY BEFORE LOAN",
			"total_prev_month": prev_gross_pay - total_prev_deduction,
			"total_cur_month": cur_gross_pay - total_cur_deduction,
			"difference_amount": h,
		}
	)

	return data


def get_prev_month_date(filters):
	prev_month = getdate(filters.from_date).month - 1
	prev_year = getdate(filters.from_date).year

	if prev_month == 0:
		prev_month = 12
		prev_year = prev_year - 1

	prev_first_date = getdate(str(prev_year) + "-" + str(prev_month) + "-" + "01")
	prev_last_date = getdate(
		str(prev_year)
		+ "-"
		+ str(prev_month)
		+ "-"
		+ "{0}".format(calendar.monthrange(prev_year, prev_month)[1])
	)

	return prev_first_date, prev_last_date, prev_month, prev_year


def get_prev_ss_basic_map(filters, prev_salary_slips):
	prev_ss_basic_query = (
		frappe.qb.from_(sd)
		.inner_join(ss)
		.on(sd.parent == ss.name)
		.select(sd.salary_component, fn.Sum(sd.amount).as_("total_prev_month"))
		.where(
			(sd.parent.isin([d.name for d in prev_salary_slips]))
			& (sd.do_not_include_in_total == 0)
			& (sd.parentfield == "earnings")
			& (sd.salary_component.like("Basic"))
		)
		.groupby(sd.salary_component)
		.orderby(sd.salary_component, order=Order.asc)
	)
	if filters.get("based_on_department") == 1:
		prev_ss_basic_query = prev_ss_basic_query.select(ss.department)
		prev_ss_basic_query = prev_ss_basic_query.groupby(ss.department)
		if filters.get("department"):
			prev_ss_basic_query = prev_ss_basic_query.where(ss.department == filters.get("department"))

	if filters.get("based_on_cost_center") == 1:
		prev_ss_basic_query = prev_ss_basic_query.select(ss.payroll_cost_center)
		prev_ss_basic_query = prev_ss_basic_query.groupby(ss.payroll_cost_center)
		if filters.get("cost_center"):
			prev_ss_basic_query = prev_ss_basic_query.where(
				ss.payroll_cost_center == filters.get("cost_center")
			)
	prev_ss_basic_query = prev_ss_basic_query.groupby(sd.salary_component)
	prev_ss_basic_data = prev_ss_basic_query.run(as_dict=1)

	return prev_ss_basic_data or []


def get_prev_ss_earn_map(filters, prev_salary_slips):
	prev_ss_earnings_query = (
		frappe.qb.from_(sd)
		.inner_join(ss)
		.on(sd.parent == ss.name)
		.select(sd.salary_component, fn.Sum(sd.amount).as_("total_prev_month"))
		.where(
			(sd.parent.isin([d.name for d in prev_salary_slips]))
			& (sd.do_not_include_in_total == 0)
			& (sd.parentfield == "earnings")
			& (sd.salary_component.not_like("Basic"))
		)
		.groupby(sd.salary_component)
		.orderby(sd.salary_component, order=Order.asc)
	)
	if filters.get("based_on_department") == 1:
		prev_ss_earnings_query = prev_ss_earnings_query.select(ss.department)
		prev_ss_earnings_query = prev_ss_earnings_query.groupby(ss.department)
		if filters.get("department"):
			prev_ss_earnings_query = prev_ss_earnings_query.where(ss.department == filters.get("department"))

	if filters.get("based_on_cost_center") == 1:
		prev_ss_earnings_query = prev_ss_earnings_query.select(ss.payroll_cost_center)
		prev_ss_earnings_query = prev_ss_earnings_query.groupby(ss.payroll_cost_center)
		if filters.get("cost_center"):
			prev_ss_earnings_query = prev_ss_earnings_query.where(
				ss.payroll_cost_center == filters.get("cost_center")
			)
	prev_ss_earnings_query = prev_ss_earnings_query.groupby(sd.salary_component)
	prev_ss_earnings_data = prev_ss_earnings_query.run(as_dict=1)

	return prev_ss_earnings_data or []


def get_prev_ss_ded_map(filters, prev_salary_slips):
	prev_ss_deductions_query = (
		frappe.qb.from_(sd)
		.inner_join(ss)
		.on(sd.parent == ss.name)
		.select(sd.salary_component, fn.Sum(sd.amount).as_("total_prev_month"))
		.where(
			(sd.parent.isin([d.name for d in prev_salary_slips]))
			& (sd.do_not_include_in_total == 0)
			& (sd.parentfield == "deductions")
		)
		.groupby(sd.salary_component)
		.orderby(sd.salary_component, order=Order.asc)
	)
	if filters.get("based_on_department") == 1:
		prev_ss_deductions_query = prev_ss_deductions_query.select(ss.department)
		prev_ss_deductions_query = prev_ss_deductions_query.groupby(ss.department)
		if filters.get("department"):
			prev_ss_deductions_query = prev_ss_deductions_query.where(
				ss.department == filters.get("department")
			)

	if filters.get("based_on_cost_center") == 1:
		prev_ss_deductions_query = prev_ss_deductions_query.select(ss.payroll_cost_center)
		prev_ss_deductions_query = prev_ss_deductions_query.groupby(ss.payroll_cost_center)
		if filters.get("cost_center"):
			prev_ss_deductions_query = prev_ss_deductions_query.where(
				ss.payroll_cost_center == filters.get("cost_center")
			)
	prev_ss_deductions_query = prev_ss_deductions_query.groupby(sd.salary_component)
	prev_ss_deductions_data = prev_ss_deductions_query.run(as_dict=1)

	return prev_ss_deductions_data or []


def get_prev_salary_slips(filters, company_currency, prev_first_date, prev_last_date):
	prev_ss_query = (
		frappe.qb.from_(ss)
		.select(ss.name)
		.where(
			(ss.docstatus == 1)
			& (ss.start_date >= prev_first_date)
			& (ss.end_date <= prev_last_date)
			& (ss.company == filters.get("company"))
		)
	)
	if filters.get("employee"):
		prev_ss_query = prev_ss_query.where(ss.employee == filters.get("employee"))

	if filters.get("currency") and filters.get("currency") != company_currency:
		prev_ss_query = prev_ss_query.where(ss.currency == filters.get("currency"))

	if filters.get("department") and filters.get("company"):
		department_list = get_departments(filters.get("department"), filters.get("company"))
		prev_ss_query = prev_ss_query.where(ss.department.isin(department_list))

	if filters.get("cost_center") and filters.get("company"):
		cost_center_list = get_cost_costs(filters.get("cost_center"), filters.get("company"))
		prev_ss_query = prev_ss_query.where(ss.payroll_cost_center.isin(cost_center_list))

	prev_salary_slips = prev_ss_query.run(as_dict=1)

	return prev_salary_slips or []


def get_cur_salary_slips(filters, company_currency):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
	cur_ss_query = (
		frappe.qb.from_(ss)
		.select(ss.name)
		.where(
			(ss.docstatus == doc_status.get(filters.get("docstatus")))
			& (ss.start_date >= filters.get("from_date"))
			& (ss.end_date <= filters.get("to_date"))
			& (ss.company == filters.get("company"))
		)
	)
	if filters.get("employee"):
		cur_ss_query = cur_ss_query.where(ss.employee == filters.get("employee"))

	if filters.get("currency") and filters.get("currency") != company_currency:
		cur_ss_query = cur_ss_query.where(ss.currency == filters.get("currency"))

	if filters.get("department") and filters.get("company"):
		department_list = get_departments(filters.get("department"), filters.get("company"))
		cur_ss_query = cur_ss_query.where(ss.department.isin(department_list))

	if filters.get("cost_center") and filters.get("company"):
		cost_center_list = get_cost_costs(filters.get("cost_center"), filters.get("company"))
		cur_ss_query = cur_ss_query.where(ss.payroll_cost_center.isin(cost_center_list))

	cur_salary_slips = cur_ss_query.run(as_dict=1)

	return cur_salary_slips or []


def get_cur_ss_basic_map(filters, cur_salary_slips):
	cur_ss_basic_query = (
		frappe.qb.from_(sd)
		.inner_join(ss)
		.on(sd.parent == ss.name)
		.select(sd.salary_component, fn.Sum(sd.amount).as_("total_cur_month"))
		.where(
			(sd.parent.isin([d.name for d in cur_salary_slips]))
			& (sd.do_not_include_in_total == 0)
			& (sd.parentfield == "earnings")
			& (sd.salary_component.like("Basic"))
		)
		.groupby(sd.salary_component)
		.orderby(sd.salary_component, order=Order.asc)
	)
	if filters.get("based_on_department") == 1:
		cur_ss_basic_query = cur_ss_basic_query.select(ss.department)
		cur_ss_basic_query = cur_ss_basic_query.groupby(ss.department)
		if filters.get("department"):
			cur_ss_basic_query = cur_ss_basic_query.where(ss.department == filters.get("department"))

	if filters.get("based_on_cost_center") == 1:
		cur_ss_basic_query = cur_ss_basic_query.select(ss.payroll_cost_center)
		cur_ss_basic_query = cur_ss_basic_query.groupby(ss.payroll_cost_center)
		if filters.get("cost_center"):
			cur_ss_basic_query = cur_ss_basic_query.where(
				ss.payroll_cost_center == filters.get("cost_center")
			)
	cur_ss_basic_query = cur_ss_basic_query.groupby(sd.salary_component)
	cur_ss_basic_data = cur_ss_basic_query.run(as_dict=1)

	return cur_ss_basic_data or []


def get_cur_ss_earning_map(filters, cur_salary_slips):
	cur_ss_earnings_query = (
		frappe.qb.from_(sd)
		.inner_join(ss)
		.on(sd.parent == ss.name)
		.select(sd.salary_component, fn.Sum(sd.amount).as_("total_cur_month"))
		.where(
			(sd.parent.isin([d.name for d in cur_salary_slips]))
			& (sd.do_not_include_in_total == 0)
			& (sd.parentfield == "earnings")
			& (sd.salary_component.not_like("Basic"))
		)
		.groupby(sd.salary_component)
		.orderby(sd.salary_component, order=Order.asc)
	)
	if filters.get("based_on_department") == 1:
		cur_ss_earnings_query = cur_ss_earnings_query.select(ss.department)
		cur_ss_earnings_query = cur_ss_earnings_query.groupby(ss.department)
		if filters.get("department"):
			cur_ss_earnings_query = cur_ss_earnings_query.where(ss.department == filters.get("department"))

	if filters.get("based_on_cost_center") == 1:
		cur_ss_earnings_query = cur_ss_earnings_query.select(ss.payroll_cost_center)
		cur_ss_earnings_query = cur_ss_earnings_query.groupby(ss.payroll_cost_center)
		if filters.get("cost_center"):
			cur_ss_earnings_query = cur_ss_earnings_query.where(
				ss.payroll_cost_center == filters.get("cost_center")
			)

	cur_ss_earnings_query = cur_ss_earnings_query.groupby(sd.salary_component)
	cur_ss_earnings_data = cur_ss_earnings_query.run(as_dict=1)

	return cur_ss_earnings_data or []


def get_cur_ss_ded_map(filters, cur_salary_slips):
	cur_ss_deduction_query = (
		frappe.qb.from_(sd)
		.inner_join(ss)
		.on(sd.parent == ss.name)
		.select(sd.salary_component, fn.Sum(sd.amount).as_("total_cur_month"))
		.where(
			(sd.parent.isin([d.name for d in cur_salary_slips]))
			& (sd.do_not_include_in_total == 0)
			& (sd.parentfield == "deductions")
		)
	)
	if filters.get("based_on_department") == 1:
		cur_ss_deduction_query = cur_ss_deduction_query.select(ss.department)
		cur_ss_deduction_query = cur_ss_deduction_query.groupby(ss.department)
		if filters.get("department"):
			cur_ss_deduction_query = cur_ss_deduction_query.where(ss.department == filters.get("department"))

	if filters.get("based_on_cost_center") == 1:
		cur_ss_deduction_query = cur_ss_deduction_query.select(ss.payroll_cost_center)
		cur_ss_deduction_query = cur_ss_deduction_query.groupby(ss.payroll_cost_center)
		if filters.get("cost_center"):
			cur_ss_deduction_query = cur_ss_deduction_query.where(
				ss.payroll_cost_center == filters.get("cost_center")
			)
	cur_ss_deduction_query = cur_ss_deduction_query.groupby(sd.salary_component)
	cur_ss_deductions_data = cur_ss_deduction_query.run(as_dict=1)

	return cur_ss_deductions_data or []


def get_departments(department, company):
	departments_list = get_descendants_of("Department", department)
	departments_list.append(department)
	return departments_list


def get_cost_costs(cost_center, company):
	cost_center_list = get_descendants_of("Cost Center", cost_center)
	cost_center_list.append(cost_center)
	return cost_center_list
