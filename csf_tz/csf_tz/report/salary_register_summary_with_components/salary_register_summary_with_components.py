# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

import erpnext
import frappe
from frappe import _
from frappe.query_builder.functions import Sum
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

	gross_pay = total_earnings + t_basic
	gp_record = {"salary_component": "GROSS PAY", "total": gross_pay}
	data.append(gp_record)

	ss_deduction_map = get_ss_ded_map(salary_slips, currency, company_currency)
	data.extend(ss_deduction_map)

	total_deduction = 0
	for deduction in ss_deduction_map:
		total_deduction = total_deduction + deduction["total"]

	netpay = gross_pay + total_deduction
	np_record = {"salary_component": "NET PAY BEFORE LOAN", "total": netpay}
	data.append(np_record)
	return data


def get_salary_slips(filters, company_currency):
	"""Select salary slips using parameterized Frappe filters."""
	filters = filters or {}
	query_filters = {}
	if filters.get("docstatus") is not None and filters.get("docstatus") != "":
		status_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
		status = status_map.get(filters["docstatus"], filters["docstatus"])
		if str(status) not in {"0", "1", "2"}:
			frappe.throw(_("Invalid Salary Slip document status"))
		query_filters["docstatus"] = int(status)
	for key, field, comparison in (
		("from_date", "start_date", ">="),
		("to_date", "end_date", "<="),
	):
		if filters.get(key):
			query_filters[field] = [comparison, filters[key]]
	for field in ("company", "employee"):
		if filters.get(field):
			query_filters[field] = filters[field]
	if filters.get("currency") and filters["currency"] != company_currency:
		query_filters["currency"] = filters["currency"]
	if filters.get("department") and filters.get("company"):
		query_filters["department"] = [
			"in",
			get_departments(filters["department"], filters["company"]),
		]
	return frappe.get_all("Salary Slip", filters=query_filters, fields=["*"], order_by="employee")


def get_ss_basic_map(salary_slips, currency, company_currency):
	if not salary_slips:
		return []
	sd = frappe.qb.DocType("Salary Detail")
	ss = frappe.qb.DocType("Salary Slip")
	query = (
		frappe.qb.from_(sd)
		.join(ss)
		.on(sd.parent == ss.name)
		.select(
			sd.salary_component,
			Sum(sd.amount).as_("total"),
		)
		.where(sd.parent.isin([slip.name for slip in salary_slips]))
		.where(sd.do_not_include_in_total == 0)
		.where(sd.parentfield == "earnings")
		.where(sd.salary_component == "Basic")
		.groupby(sd.salary_component)
		.orderby(sd.salary_component)
	)
	return query.run(as_dict=True)


def get_ss_earning_map(salary_slips, currency, company_currency):
	if not salary_slips:
		return []
	sd = frappe.qb.DocType("Salary Detail")
	ss = frappe.qb.DocType("Salary Slip")
	query = (
		frappe.qb.from_(sd)
		.join(ss)
		.on(sd.parent == ss.name)
		.select(
			sd.salary_component,
			Sum(sd.amount).as_("total"),
		)
		.where(sd.parent.isin([slip.name for slip in salary_slips]))
		.where(sd.do_not_include_in_total == 0)
		.where(sd.parentfield == "earnings")
		.where(sd.salary_component != "Basic")
		.groupby(sd.salary_component)
		.orderby(sd.salary_component)
	)
	return query.run(as_dict=True)


def get_ss_ded_map(salary_slips, currency, company_currency):
	if not salary_slips:
		return []
	sd = frappe.qb.DocType("Salary Detail")
	ss = frappe.qb.DocType("Salary Slip")
	query = (
		frappe.qb.from_(sd)
		.join(ss)
		.on(sd.parent == ss.name)
		.select(
			sd.salary_component,
			(Sum(sd.amount) * -1).as_("total"),
		)
		.where(sd.parent.isin([slip.name for slip in salary_slips]))
		.where(sd.do_not_include_in_total == 0)
		.where(sd.parentfield == "deductions")
		.groupby(sd.salary_component)
		.orderby(sd.salary_component)
	)
	return query.run(as_dict=True)


def get_departments(department, company):
	departments_list = get_descendants_of("Department", department)
	departments_list.append(department)
	return departments_list
