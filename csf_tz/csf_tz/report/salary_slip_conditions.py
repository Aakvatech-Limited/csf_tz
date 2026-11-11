import frappe
from frappe.utils.nestedset import get_descendants_of


def get_currency_and_department_conditions(salary_slip, filters, company_currency):
	conditions = []
	if filters.get("currency") and filters.get("currency") != company_currency:
		conditions.append(salary_slip.currency == filters.get("currency"))
	if filters.get("department") and filters.get("company"):
		department_list = get_departments(filters.get("department"), filters.get("company"))
		conditions.append(salary_slip.department.isin(department_list))
	return conditions


def get_departments(department, company):
	departments_list = get_descendants_of("Department", department)
	departments_list.append(department)
	return departments_list


def get_salary_component_totals_query(salary_slips, parentfield):
	"""Salary Detail rows of the given slips, grouped by component; callers add the total column."""
	salary_detail = frappe.qb.DocType("Salary Detail")
	salary_slip = frappe.qb.DocType("Salary Slip")
	return (
		frappe.qb.from_(salary_detail)
		.inner_join(salary_slip)
		.on(salary_detail.parent == salary_slip.name)
		.select(salary_detail.salary_component)
		.where(
			salary_detail.parent.isin([d.name for d in salary_slips])
			& (salary_detail.do_not_include_in_total == 0)
			& (salary_detail.parentfield == parentfield)
		)
		.groupby(salary_detail.salary_component)
		.orderby(salary_detail.salary_component)
	)
