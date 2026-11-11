import frappe
from frappe import _
from frappe.query_builder import Criterion
from frappe.utils import cint
from frappe.utils.nestedset import get_descendants_of

DOCSTATUS_BY_LABEL = {"Draft": 0, "Submitted": 1, "Cancelled": 2}


def get_docstatus_condition(salary_slip, filters):
	"""Docstatus criterion; the filter is required."""
	docstatus = filters.get("docstatus")
	if not docstatus:
		frappe.throw(_("Please set the Document Status filter"))
	return salary_slip.docstatus == DOCSTATUS_BY_LABEL.get(docstatus, cint(docstatus))


def get_salary_slip_conditions(salary_slip, filters, company_currency, from_date, to_date):
	conditions = []
	if from_date:
		conditions.append(salary_slip.start_date >= from_date)
	if to_date:
		conditions.append(salary_slip.end_date <= to_date)
	for fieldname in ("company", "employee"):
		if filters.get(fieldname):
			conditions.append(salary_slip[fieldname] == filters.get(fieldname))
	if filters.get("currency") and filters.get("currency") != company_currency:
		conditions.append(salary_slip.currency == filters.get("currency"))
	if filters.get("department") and filters.get("company"):
		conditions.append(salary_slip.department.isin(get_departments(filters.get("department"))))
	return conditions


def get_current_period_conditions(salary_slip, filters, company_currency):
	return [
		get_docstatus_condition(salary_slip, filters),
		*get_salary_slip_conditions(
			salary_slip, filters, company_currency, filters.get("from_date"), filters.get("to_date")
		),
	]


def get_salary_slips(filters, company_currency, extra_conditions=None):
	"""All Salary Slip columns for the current-period filters, ordered by employee."""
	filters.update({"from_date": filters.get("from_date"), "to_date": filters.get("to_date")})
	salary_slip = frappe.qb.DocType("Salary Slip")
	conditions = get_current_period_conditions(salary_slip, filters, company_currency)
	return (
		frappe.qb.from_(salary_slip)
		.select(salary_slip.star)
		.where(Criterion.all(conditions + (extra_conditions or [])))
		.orderby(salary_slip.employee)
		.run(as_dict=True)
	)


def get_departments(department):
	departments_list = get_descendants_of("Department", department)
	departments_list.append(department)
	return departments_list


def get_salary_component_totals_query(salary_slips, parentfield):
	"""Salary Detail rows of the given slips grouped by component; callers add the total column."""
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
