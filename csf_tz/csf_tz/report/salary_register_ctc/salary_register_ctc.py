# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

import frappe
import erpnext
from frappe.utils import flt
from frappe import _, msgprint
from frappe.query_builder import Criterion
from csf_tz.csf_tz.report.salary_slip_conditions import (
    get_currency_and_department_conditions,
)


def execute(filters=None):
    if not filters:
        filters = {}
    currency = None
    if filters.get("currency"):
        currency = filters.get("currency")
    company_currency = erpnext.get_company_currency(filters.get("company"))
    salary_slips = get_salary_slips(filters, company_currency)
    if not salary_slips:
        return [], []

    columns, earning_types, ded_types, ded_types_ctc = get_columns(salary_slips)
    ss_earning_map = get_ss_earning_map(salary_slips, currency, company_currency)
    ss_ded_map = get_ss_ded_map(salary_slips, currency, company_currency)
    doj_map = get_employee_doj_map()
    
    data = []
    for ss in salary_slips:
        CTC = ss.gross_pay
        row = [
            ss.name,
            ss.employee,
            ss.employee_name,
            doj_map.get(ss.employee),
            ss.branch,
            ss.department,
            ss.designation,
            ss.company,
            ss.start_date,
            ss.end_date,
            ss.leave_without_pay,
            ss.payment_days,
        ]

        if ss.branch is not None:
            columns[3] = columns[3].replace("-1", "120")
        if ss.department is not None:
            columns[4] = columns[4].replace("-1", "120")
        if ss.designation is not None:
            columns[5] = columns[5].replace("-1", "120")
        if ss.leave_without_pay is not None:
            columns[9] = columns[9].replace("-1", "130")

        for e in earning_types:
            row.append(ss_earning_map.get(ss.name, {}).get(e))

        if currency == company_currency:
            row += [flt(ss.gross_pay) * flt(ss.exchange_rate)]
        else:
            row += [ss.gross_pay]

        for d in ded_types:
            row.append(ss_ded_map.get(ss.name, {}).get(d))

        row.append(ss.total_loan_repayment)

        if currency == company_currency:
            row += [
                flt(ss.total_deduction) * flt(ss.exchange_rate),
                flt(ss.net_pay) * flt(ss.exchange_rate),
            ]
        else:
            row += [ss.total_deduction, ss.net_pay]

        for d_ctc in ded_types_ctc:
            amount = flt(ss_ded_map.get(ss.name, {}).get(d_ctc))
            CTC = CTC + amount
            row.append(amount)
            
        row.append(CTC)
        row.append(currency or company_currency)
        data.append(row)
    
    columns += [_("CTC") + ":Currency:120"]

    return columns, data


def get_columns(salary_slips):
    """
    columns = [
        _("Salary Slip ID") + ":Link/Salary Slip:150",
        _("Employee") + ":Link/Employee:120",
        _("Employee Name") + "::140",
        _("Date of Joining") + "::80",
        _("Branch") + ":Link/Branch:120",
        _("Department") + ":Link/Department:120",
        _("Designation") + ":Link/Designation:120",
        _("Company") + ":Link/Company:120",
        _("Start Date") + "::80",
        _("End Date") + "::80",
        _("Leave Without Pay") + ":Float:130",
        _("Payment Days") + ":Float:120",
        _("Currency") + ":Link/Currency:80"
    ]
    """
    columns = [
        _("Salary Slip ID") + ":Link/Salary Slip:150",
        _("Employee") + ":Link/Employee:120",
        _("Employee Name") + "::140",
        _("Date of Joining") + "::80",
        _("Branch") + ":Link/Branch:-1",
        _("Department") + ":Link/Department:-1",
        _("Designation") + ":Link/Designation:120",
        _("Company") + ":Link/Company:120",
        _("Start Date") + "::80",
        _("End Date") + "::80",
        _("Leave Without Pay") + ":Float:50",
        _("Payment Days") + ":Float:120",
    ]

    salary_components = {_("Earning"): [], _("Deduction"): []}

    for component in get_salary_components(salary_slips, do_not_include_in_total=0):
        salary_components[_(component.type)].append(component.salary_component)

    columns = (
        columns
        + [(e + ":Currency:120") for e in salary_components[_("Earning")]]
        + [_("Gross Pay") + ":Currency:120"]
        + [(d + ":Currency:120") for d in salary_components[_("Deduction")]]
        + [
            _("Loan Repayment") + ":Currency:120",
            _("Total Deduction") + ":Currency:120",
            _("Net Pay") + ":Currency:120",
        ]
    )
    components = {_("Deduction"): []}
    company_expenses = get_salary_components(
        salary_slips, do_not_include_in_total=1, component_type="Deduction"
    )
    for entry in company_expenses:
        components[_(entry.type)].append(entry.salary_component)
    
    columns = (columns + [(d_ctc + ":Currency:120") for d_ctc in components[_("Deduction")]])

    return columns, salary_components[_("Earning")], salary_components[_("Deduction")], components[_("Deduction")]


def get_salary_components(salary_slips, do_not_include_in_total, component_type=None):
    salary_detail = frappe.qb.DocType("Salary Detail")
    salary_component = frappe.qb.DocType("Salary Component")
    query = (
        frappe.qb.from_(salary_detail)
        .inner_join(salary_component)
        .on(salary_component.name == salary_detail.salary_component)
        .select(salary_detail.salary_component, salary_component.type)
        .distinct()
        .where(
            (salary_component.do_not_include_in_total == do_not_include_in_total)
            & (salary_detail.amount != 0)
            & salary_detail.parent.isin([d.name for d in salary_slips])
        )
    )
    if component_type:
        query = query.where(salary_component.type == component_type)
    return query.run(as_dict=True)


def get_salary_slips(filters, company_currency):
    filters.update(
        {"from_date": filters.get("from_date"), "to_date": filters.get("to_date")}
    )
    salary_slip = frappe.qb.DocType("Salary Slip")
    salary_slips = (
        frappe.qb.from_(salary_slip)
        .select(salary_slip.star)
        .where(Criterion.all(get_conditions(salary_slip, filters, company_currency)))
        .orderby(salary_slip.employee)
        .run(as_dict=True)
    )

    return salary_slips or []


def get_conditions(salary_slip, filters, company_currency):
    conditions = []
    doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

    if filters.get("docstatus"):
        conditions.append(salary_slip.docstatus == doc_status[filters.get("docstatus")])
    if filters.get("from_date"):
        conditions.append(salary_slip.start_date >= filters.get("from_date"))
    if filters.get("to_date"):
        conditions.append(salary_slip.end_date <= filters.get("to_date"))
    for fieldname in ("company", "employee", "workflow_state"):
        if filters.get(fieldname):
            conditions.append(salary_slip[fieldname] == filters.get(fieldname))

    return conditions + get_currency_and_department_conditions(
        salary_slip, filters, company_currency
    )


def get_employee_doj_map():
    employee = frappe.qb.DocType("Employee")
    return frappe._dict(
        frappe.qb.from_(employee)
        .select(employee.employee, employee.date_of_joining)
        .run()
    )


def get_salary_details(salary_slips):
    salary_detail = frappe.qb.DocType("Salary Detail")
    salary_slip = frappe.qb.DocType("Salary Slip")
    return (
        frappe.qb.from_(salary_detail)
        .inner_join(salary_slip)
        .on(salary_detail.parent == salary_slip.name)
        .select(
            salary_detail.parent,
            salary_detail.salary_component,
            salary_detail.amount,
            salary_slip.exchange_rate,
            salary_slip.name,
        )
        .where(salary_detail.parent.isin([d.name for d in salary_slips]))
        .run(as_dict=True)
    )


def get_ss_earning_map(salary_slips, currency, company_currency):
    ss_earnings = get_salary_details(salary_slips)

    ss_earning_map = {}
    for d in ss_earnings:
        ss_earning_map.setdefault(d.parent, frappe._dict()).setdefault(
            d.salary_component, []
        )
        if currency == company_currency:
            ss_earning_map[d.parent][d.salary_component] = flt(d.amount) * flt(
                d.exchange_rate if d.exchange_rate else 1
            )
        else:
            ss_earning_map[d.parent][d.salary_component] = flt(d.amount)

    return ss_earning_map


def get_ss_ded_map(salary_slips, currency, company_currency):
    ss_deductions = get_salary_details(salary_slips)

    ss_ded_map = {}
    for d in ss_deductions:
        ss_ded_map.setdefault(d.parent, frappe._dict()).setdefault(
            d.salary_component, []
        )
        if currency == company_currency:
            ss_ded_map[d.parent][d.salary_component] = flt(d.amount) * flt(
                d.exchange_rate if d.exchange_rate else 1
            )
        else:
            ss_ded_map[d.parent][d.salary_component] = flt(d.amount)
        
    return ss_ded_map


@frappe.whitelist()
def approve(data):
    from frappe.utils.background_jobs import enqueue
    import json

    data = json.loads(data)
    enqueue(
        method=enqueue_approve,
        queue="short",
        timeout=10000,
        job_name="approve_salary_slip",
        is_async=True,
        kwargs=data,
    )
    return _("Start Processing")


def enqueue_approve(kwargs):
    from frappe.model.workflow import apply_workflow

    data = kwargs
    for i in data:
        if not i.get("salary_slip_id") or i.get("salary_slip_id") == "Total":
            continue
        doc = frappe.get_doc("Salary Slip", i.get("salary_slip_id"))
        if doc.workflow_state == "Pending":
            try:
                apply_workflow(doc, "Approve")
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(e)

