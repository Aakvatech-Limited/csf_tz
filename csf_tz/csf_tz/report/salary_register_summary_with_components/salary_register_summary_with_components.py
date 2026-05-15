# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import erpnext
import frappe
from frappe import _
from frappe.utils.nestedset import get_descendants_of


def execute(filters=None):
	columns = [
		{"fieldname": "salary_component", "label": _("Salary Component"), "fieldtype": "Data", "width": 300},
		{"fieldname": "total", "label": _("Total"), "fieldtype": "Float", "width": 300, "precision": 2},
	]
	data = get_data(filters)
	return columns, data


def get_data(filters=None):
	if not filters:
		filters = {}
	currency = None
	data = []
	if filters.get("currency"):
		currency = filters.get("currency")
	company_currency = erpnext.get_company_currency(filters.get("company"))
	salary_slips = get_salary_slips(filters, company_currency)
	if not salary_slips:
		return []

	blank_line = {"salary_component": "", "total": ""}
	total_employees = len(salary_slips)
	# frappe.msgprint(str(total_employees))
	total_employee_record = {"salary_component": "Total Employees", "total": total_employees}
	data.append(total_employee_record)
	data.append(blank_line)

	ss_basic_map = get_ss_basic_map(salary_slips, currency, company_currency)
	data.extend(ss_basic_map)
	t_basic = 0
	for basic in ss_basic_map:
		t_basic = t_basic + basic["total"]

	ss_earning_map = get_ss_earning_map(salary_slips, currency, company_currency)
	data.extend(ss_earning_map)

	# frappe.msgprint(str(ss_earning_map))
	total_earnings = 0
	for earning in ss_earning_map:
		total_earnings = total_earnings + earning["total"]
	# data.append(te_record)

	gross_pay = total_earnings + t_basic
	gp_record = {"salary_component": "GROSS PAY", "total": gross_pay}
	data.append(gp_record)

	ss_deduction_map = get_ss_ded_map(salary_slips, currency, company_currency)
	data.extend(ss_deduction_map)

	total_deduction = 0
	for deduction in ss_deduction_map:
		total_deduction = total_deduction + deduction["total"]

	# data.append(ded_record)

	netpay = gross_pay + total_deduction
	np_record = {"salary_component": "NET PAY BEFORE LOAN", "total": netpay}
	data.append(np_record)
	return data


def get_salary_slips(filters, company_currency):
	filters.update({"from_date": filters.get("from_date"), "to_date": filters.get("to_date")})
	conditions, filters = get_conditions(filters, company_currency)
	salary_slips = frappe.db.sql(
		"""select * from `tabSalary Slip` where %s
        order by employee"""
		% conditions,
		filters,
		as_dict=1,
	)

	return salary_slips or []


def get_ss_basic_map(salary_slips, currency, company_currency):
	ss_basic = frappe.db.sql(
		"""
        SELECT sd.salary_component, SUM(sd.amount) as total
        FROM `tabSalary Detail` sd, `tabSalary Slip` ss where sd.parent=ss.name
        AND sd.parent in (%s)
        AND do_not_include_in_total = 0
        AND sd.parentfield = 'earnings'
        AND sd.salary_component = 'Basic'
        GROUP BY sd.salary_component
        ORDER BY sd.salary_component ASC"""
		% (", ".join(["%s"] * len(salary_slips))),
		tuple([d.name for d in salary_slips]),
		as_dict=1,
	)

	return ss_basic


def get_ss_earning_map(salary_slips, currency, company_currency):
	ss_earnings = frappe.db.sql(
		"""
        SELECT sd.salary_component, SUM(sd.amount) as total
        FROM `tabSalary Detail` sd, `tabSalary Slip` ss where sd.parent=ss.name
        AND sd.parent in (%s)
        AND do_not_include_in_total = 0
        AND sd.parentfield = 'earnings'
        AND sd.salary_component != 'Basic'
        GROUP BY sd.salary_component
        ORDER BY sd.salary_component ASC"""
		% (", ".join(["%s"] * len(salary_slips))),
		tuple([d.name for d in salary_slips]),
		as_dict=1,
	)

	return ss_earnings


def get_ss_ded_map(salary_slips, currency, company_currency):
	ss_deductions = frappe.db.sql(
		"""
        SELECT sd.salary_component, SUM(sd.amount) * -1 as total
        FROM `tabSalary Detail` sd, `tabSalary Slip` ss where sd.parent=ss.name AND sd.parent in (%s)
        AND do_not_include_in_total = 0
        AND sd.parentfield = 'deductions'
        GROUP BY sd.salary_component
        ORDER BY sd.salary_component ASC"""
		% (", ".join(["%s"] * len(salary_slips))),
		tuple([d.name for d in salary_slips]),
		as_dict=1,
	)
	return ss_deductions


def get_conditions(filters, company_currency):
	conditions = ""
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	if filters.get("docstatus"):
		conditions += "docstatus = {0}".format(doc_status[filters.get("docstatus")])

	if filters.get("from_date"):
		conditions += " and start_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " and end_date <= %(to_date)s"
	if filters.get("company"):
		conditions += " and company = %(company)s"
	if filters.get("employee"):
		conditions += " and employee = %(employee)s"
	if filters.get("currency") and filters.get("currency") != company_currency:
		conditions += " and currency = %(currency)s"
	if filters.get("department") and filters.get("company"):
		department_list = get_departments(filters.get("department"), filters.get("company"))
		conditions += "and department in (" + ",".join(("'" + n + "'" for n in department_list)) + ")"

	return conditions, filters


def get_departments(department, company):
	departments_list = get_descendants_of("Department", department)
	departments_list.append(department)
	return departments_list
