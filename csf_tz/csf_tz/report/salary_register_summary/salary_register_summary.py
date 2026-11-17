# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe.utils import flt
from frappe import _, msgprint
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Sum
from csf_tz.csf_tz.report.salary_slip_conditions import (
    get_currency_and_department_conditions,
    get_salary_component_totals_query,
)


def execute(filters=None):
    columns = [{
        "fieldname": "salary_component",
        "label": _("Salary Component"),
        "fieldtype": "Data",
        "width": 300
    },
        {
        "fieldname": "total",
        "label": _("Total"),
        "fieldtype": "Float",
        "width": 300
    }]
    data = get_data(filters)
    return columns, data


def get_data(filters=None):
    if not filters:
        filters = {}
    currency = None
    data = []
    if filters.get('currency'):
        currency = filters.get('currency')
    company_currency = erpnext.get_company_currency(filters.get("company"))
    salary_slips = get_salary_slips(filters, company_currency)
    if not salary_slips:
        return []

    blank_line = {"salary_component": "", "total": ""}
    total_employees = len(salary_slips)
    #frappe.msgprint(str(total_employees))
    total_employee_record = {
        "salary_component": "Total Employees", "total": total_employees}
    data.append(total_employee_record)
    data.append(blank_line)

    ss_basic_map = get_ss_basic_map(salary_slips, currency, company_currency)
    data.extend(ss_basic_map)
    t_basic = 0
    for basic in ss_basic_map:
        t_basic = t_basic + basic["total"]

    ss_earning_map = get_ss_earning_map(salary_slips, currency, company_currency)
    #data.extend(ss_earning_map)
    
    #frappe.msgprint(str(ss_earning_map))
    total_earnings = 0
    for earning in ss_earning_map:
         total_earnings = total_earnings + earning["total"]
    te_record = {"salary_component": "Total Allowances", "total": total_earnings}
    data.append(te_record)

    gross_pay = total_earnings + t_basic
    gp_record = {"salary_component": "GROSS PAY", "total": gross_pay}
    data.append(gp_record)

    ss_deduction_map = get_ss_ded_map(salary_slips, currency, company_currency)
    #data.extend(ss_deduction_map)

    total_deduction = 0
    for deduction in ss_deduction_map:
        total_deduction = total_deduction + deduction["total"]
        
    ded_record = {"salary_component": "Total Deductions", "total": total_deduction}
    data.append(ded_record)

    netpay = gross_pay + total_deduction
    np_record = {"salary_component": "NET PAY", "total": netpay}
    data.append(np_record)

    # ss_ded_map = get_ss_ded_map(salary_slips, currency, company_currency)
    # data.extend(ss_ded_map)
    return data


def get_salary_slips(filters, company_currency):
    filters.update({"from_date": filters.get("from_date"),
                    "to_date": filters.get("to_date")})
    salary_slip = frappe.qb.DocType("Salary Slip")
    salary_slips = (
        frappe.qb.from_(salary_slip)
        .select(salary_slip.star)
        .where(Criterion.all(get_conditions(salary_slip, filters, company_currency)))
        .orderby(salary_slip.employee)
        .run(as_dict=True)
    )

    return salary_slips or []


def get_ss_basic_map(salary_slips, currency, company_currency):
    salary_detail = frappe.qb.DocType("Salary Detail")
    ss_basic = (
        get_salary_component_totals_query(salary_slips, "earnings")
        .select(Sum(salary_detail.amount).as_("total"))
        .where(salary_detail.salary_component == "Basic")
        .run(as_dict=True)
    )

    return ss_basic



def get_ss_earning_map(salary_slips, currency, company_currency):
    salary_detail = frappe.qb.DocType("Salary Detail")
    ss_earnings = (
        get_salary_component_totals_query(salary_slips, "earnings")
        .select(Sum(salary_detail.amount).as_("total"))
        .where(salary_detail.salary_component != "Basic")
        .run(as_dict=True)
    )

    return ss_earnings


def get_ss_ded_map(salary_slips, currency, company_currency):
    salary_detail = frappe.qb.DocType("Salary Detail")
    ss_deductions = (
        get_salary_component_totals_query(salary_slips, "deductions")
        .select((Sum(salary_detail.amount) * -1).as_("total"))
        .run(as_dict=True)
    )
    return ss_deductions


def get_conditions(salary_slip, filters, company_currency):
    conditions = []
    doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

    if filters.get("docstatus"):
        conditions.append(salary_slip.docstatus == doc_status[filters.get("docstatus")])
    if filters.get("from_date"):
        conditions.append(salary_slip.start_date >= filters.get("from_date"))
    if filters.get("to_date"):
        conditions.append(salary_slip.end_date <= filters.get("to_date"))
    for fieldname in ("company", "employee"):
        if filters.get(fieldname):
            conditions.append(salary_slip[fieldname] == filters.get(fieldname))

    return conditions + get_currency_and_department_conditions(
        salary_slip, filters, company_currency
    )
