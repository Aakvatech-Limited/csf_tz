from __future__ import unicode_literals
import frappe

def execute():
    salary_slip = frappe.qb.DocType("Salary Slip").as_("salary_slip")
    employee = frappe.qb.DocType("Employee")
    (
        frappe.qb.update(salary_slip)
        .inner_join(employee)
        .on(salary_slip.employee == employee.name)
        .set(salary_slip.payroll_cost_center, employee.payroll_cost_center)
        .where(salary_slip.payroll_cost_center.isnull())
    ).run()
