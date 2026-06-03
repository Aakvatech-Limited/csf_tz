# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt


import erpnext
import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import get_descendants_of

# nosemgrep: frappe-semgrep-rules.rules.frappe-breaks-multitenancy
salary_slip = frappe.qb.DocType("Salary Slip")
# nosemgrep: frappe-semgrep-rules.rules.frappe-breaks-multitenancy
salary_detail = frappe.qb.DocType("Salary Detail")
# nosemgrep: frappe-semgrep-rules.rules.frappe-breaks-multitenancy
salary_component = frappe.qb.DocType("Salary Component")


def execute(filters=None):
	if not filters:
		filters = {}
	currency = None
	if filters.get("currency"):
		currency = filters.get("currency")
	company_currency = erpnext.get_company_currency(filters.get("company"))

	if currency and currency == company_currency and filters.get("multi_currency"):
		frappe.throw(
			_(
				f"Currency: <b>{currency}</b> on report filters and default company currency: <b>{company_currency}</b> cannot be same for Multi Currency Report, please change one of them."
			)
		)

	salary_slips = get_salary_slips(filters)
	if not salary_slips:
		frappe.msgprint(_("<b>No record found for the filters above</b>"))
		return [], []

	return get_data(filters, salary_slips, currency, company_currency)


def get_data(filters, salary_slips, currency, company_currency):
	earning_types, ded_types = get_earning_and_deduction_types(salary_slips)
	columns = get_columns(filters, company_currency, earning_types, ded_types)

	ss_earning_map = get_salary_slip_details(salary_slips, currency, company_currency, "earnings")
	ss_ded_map = get_salary_slip_details(salary_slips, currency, company_currency, "deductions")

	doj_map = get_employee_doj_map()

	data = []
	replace_currency_label = False
	unique_columns = [column.get("fieldname") for column in columns]
	for ss in salary_slips:
		row = {
			"salary_slip_id": ss.name,
			"employee": ss.employee,
			"employee_name": ss.employee_name,
			"data_of_joining": doj_map.get(ss.employee),
			"branch": ss.branch,
			"department": ss.department,
			"designation": ss.designation,
			"company": ss.company,
			"start_date": ss.start_date,
			"end_date": ss.end_date,
			"payment_days": ss.payment_days,
			"currency": ss.currency,
		}
		if filters.get("multi_currency") and ss.currency != company_currency:
			row["exchange_rate"] = ss.exchange_rate

			if "exchange_rate" not in unique_columns:
				columns.append(
					{
						"label": _("Exchange Rate"),
						"fieldname": "exchange_rate",
						"fieldtype": "Float",
						"width": 120,
					}
				)
				unique_columns.append("exchange_rate")

		row["leave_without_pay"] = ss.leave_without_pay
		if "leave_without_pay" not in unique_columns:
			columns.append(
				{
					"label": _("Leave Without Pay"),
					"fieldname": "leave_without_pay",
					"fieldtype": "Currency",
					"options": "currency",
					"width": 100,
				}
			)
			unique_columns.append("leave_without_pay")

		if filters.get("multi_currency") and ss.currency != company_currency:
			row["leave_without_pay_" + str(company_currency).lower()] = flt(ss.leave_without_pay) * flt(
				ss.exchange_rate
			)

			if "leave_without_pay_" + str(company_currency).lower() not in unique_columns:
				columns.append(
					{
						"label": _(f"Leave Without Pay {company_currency}"),
						"fieldname": "leave_without_pay_" + str(company_currency).lower(),
						"fieldtype": "Currency",
						"options": "company_currency",
						"width": 120,
					}
				)
				unique_columns.append("leave_without_pay_" + str(company_currency).lower())

		update_column_width(ss, columns)

		for e in earning_types:
			row.update({frappe.scrub(e): ss_earning_map.get(ss.name, {}).get(e)})
			if frappe.scrub(e) not in unique_columns:
				columns.append(
					{
						"label": e,
						"fieldname": frappe.scrub(e),
						"fieldtype": "Currency",
						"options": "currency",
						"width": 120,
					}
				)
				unique_columns.append(frappe.scrub(e))

			if filters.get("multi_currency") and ss.currency != company_currency:
				e_amount = ss_earning_map.get(ss.name, {}).get(e) or 0
				row.update(
					{frappe.scrub(e) + "_" + str(company_currency).lower(): e_amount * flt(ss.exchange_rate)}
				)

				if frappe.scrub(e) + "_" + str(company_currency).lower() not in unique_columns:
					columns.append(
						{
							"label": e + " " + str(company_currency),
							"fieldname": frappe.scrub(e) + "_" + str(company_currency).lower(),
							"fieldtype": "Currency",
							"options": "company_currency",
							"width": 120,
						}
					)
					unique_columns.append(frappe.scrub(e) + "_" + str(company_currency).lower())

		row["gross_pay"] = ss.gross_pay
		if "gross_pay" not in unique_columns:
			columns.append(
				{
					"label": _("Gross Pay"),
					"fieldname": "gross_pay",
					"fieldtype": "Currency",
					"options": "currency",
					"width": 120,
				}
			)
			unique_columns.append("gross_pay")

		if filters.get("multi_currency") and ss.currency != company_currency:
			row.update(
				{
					"gross_pay_" + str(company_currency).lower(): flt(ss.gross_pay) * flt(ss.exchange_rate),
				}
			)

			if "gross_pay_" + str(company_currency).lower() not in unique_columns:
				columns.append(
					{
						"label": _(f"Gross Pay {company_currency}"),
						"fieldname": "gross_pay_" + str(company_currency).lower(),
						"fieldtype": "Currency",
						"options": "company_currency",
						"width": 120,
					}
				)
				unique_columns.append("gross_pay_" + str(company_currency).lower())

		for d in ded_types:
			row.update({frappe.scrub(d): ss_ded_map.get(ss.name, {}).get(d)})
			if frappe.scrub(d) not in unique_columns:
				columns.append(
					{
						"label": d,
						"fieldname": frappe.scrub(d),
						"fieldtype": "Currency",
						"options": "currency",
						"width": 120,
					}
				)
				unique_columns.append(frappe.scrub(d))

			if filters.get("multi_currency") and ss.currency != company_currency:
				d_amount = ss_ded_map.get(ss.name, {}).get(d) or 0
				row.update(
					{frappe.scrub(d) + "_" + str(company_currency).lower(): d_amount * flt(ss.exchange_rate)}
				)
				if frappe.scrub(d) + "_" + str(company_currency).lower() not in unique_columns:
					columns.append(
						{
							"label": d + " " + str(company_currency),
							"fieldname": frappe.scrub(d) + "_" + str(company_currency).lower(),
							"fieldtype": "Currency",
							"options": "company_currency",
							"width": 120,
						}
					)
					unique_columns.append(frappe.scrub(d) + "_" + str(company_currency).lower())

		row.update(
			{
				"loan_repayment": ss.total_loan_repayment,
				"total_deduction": ss.total_deduction,
				"net_pay": ss.net_pay,
			}
		)
		if filters.get("multi_currency") and ss.currency != company_currency:
			row.update(
				{
					"loan_repayment_" + str(company_currency).lower(): flt(ss.total_loan_repayment)
					* flt(ss.exchange_rate),
					"total_deduction_" + str(company_currency).lower(): flt(ss.total_deduction)
					* flt(ss.exchange_rate),
					"net_pay_" + str(company_currency).lower(): flt(ss.net_pay) * flt(ss.exchange_rate),
				}
			)

		for field in ["loan_repayment", "total_deduction", "net_pay"]:
			if field not in unique_columns:
				columns.append(
					{
						"label": _(frappe.unscrub(field)),
						"fieldname": field,
						"fieldtype": "Currency",
						"options": "currency",
						"width": 120,
					}
				)
				unique_columns.append(field)

			if filters.get("multi_currency") and ss.currency != company_currency:
				report_fieldname = field + "_" + str(company_currency).lower()
				if report_fieldname not in unique_columns:
					columns.append(
						{
							"label": _(f"{frappe.unscrub(field)} {company_currency}"),
							"fieldname": report_fieldname,
							"fieldtype": "Currency",
							"options": "company_currency",
							"width": 120,
						}
					)
					unique_columns.append(report_fieldname)

		data.append(row)

		if not replace_currency_label:
			for col in columns:
				if (
					# col.get("options") == "currency"
					company_currency in col["label"]
				):
					col["label"] = col["label"].replace(ss.currency, "")
			replace_currency_label = True

	return columns, data


def get_earning_and_deduction_types(salary_slips):
	salary_component_and_type = {_("Earning"): [], _("Deduction"): []}
	salary_components = get_salary_components(salary_slips)

	for component in salary_components:
		component_type = get_salary_component_type(component.salary_component)
		salary_component_and_type[_(component_type)].append(component.salary_component)
	return sorted(salary_component_and_type[_("Earning")]), sorted(salary_component_and_type[_("Deduction")])


def update_column_width(ss, columns):
	if ss.branch is not None:
		columns[3].update({"width": 120})
	if ss.department is not None:
		columns[4].update({"width": 120})
	if ss.designation is not None:
		columns[5].update({"width": 120})
	if ss.leave_without_pay is not None:
		columns[9].update({"width": 120})


def get_columns(filters, company_currency, earning_types, ded_types):
	columns = [
		{
			"label": _("Salary Slip ID"),
			"fieldname": "salary_slip_id",
			"fieldtype": "Link",
			"options": "Salary Slip",
			"width": 150,
		},
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Date of Joining"),
			"fieldname": "data_of_joining",
			"fieldtype": "Date",
			"width": 80,
		},
		{
			"label": _("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": "Branch",
			"width": -1,
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": -1,
		},
		{
			"label": _("Designation"),
			"fieldname": "designation",
			"fieldtype": "Link",
			"options": "Designation",
			"width": 120,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		},
		{
			"label": _("Start Date"),
			"fieldname": "start_date",
			"fieldtype": "Date",
			"width": 80,
		},
		{
			"label": _("End Date"),
			"fieldname": "end_date",
			"fieldtype": "Date",
			"width": 80,
		},
		# {
		#     "label": _("Currency"),
		#     "fieldtype": "Link",
		#     "fieldname": "currency",
		#     "options": "Currency",
		#     "hidden": 1,
		# },
		{
			"label": _("Payment Days"),
			"fieldname": "payment_days",
			"fieldtype": "Int",
			"width": 120,
		},
	]
	return columns


def get_salary_components(salary_slips):
	return (
		frappe.qb.from_(salary_detail)
		.where((salary_detail.amount != 0) & (salary_detail.parent.isin([d.name for d in salary_slips])))
		.select(salary_detail.salary_component)
		.distinct()
	).run(as_dict=True)


def get_salary_component_type(salary_component):
	return frappe.db.get_value("Salary Component", salary_component, "type", cache=True)


def get_salary_slips(filters):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	query = frappe.qb.from_(salary_slip).select(salary_slip.star)

	if filters.get("docstatus"):
		query = query.where(salary_slip.docstatus == doc_status[filters.get("docstatus")])

	if filters.get("from_date"):
		query = query.where(salary_slip.start_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(salary_slip.end_date <= filters.get("to_date"))

	if filters.get("company"):
		query = query.where(salary_slip.company == filters.get("company"))

	if filters.get("employee"):
		query = query.where(salary_slip.employee == filters.get("employee"))

	if filters.get("currency") and filters.get("currency"):
		query = query.where(salary_slip.currency == filters.get("currency"))
	if filters.get("department") and filters.get("company"):
		department_list = get_departments(filters.get("department"), filters.get("company"))
		query = query.where(salary_slip.department.isin(department_list))

	salary_slips = query.run(as_dict=1)

	return salary_slips or []


def get_employee_doj_map():
	employee = frappe.qb.DocType("Employee")

	result = (frappe.qb.from_(employee).select(employee.name, employee.date_of_joining)).run()

	return frappe._dict(result)


def get_salary_slip_details(salary_slips, currency, company_currency, component_type):
	salary_slips = [ss.name for ss in salary_slips]

	result = (
		frappe.qb.from_(salary_slip)
		.join(salary_detail)
		.on(salary_slip.name == salary_detail.parent)
		.where((salary_detail.parent.isin(salary_slips)) & (salary_detail.parentfield == component_type))
		.select(
			salary_detail.parent,
			salary_detail.salary_component,
			salary_detail.amount,
			salary_slip.exchange_rate,
		)
	).run(as_dict=1)

	ss_map = {}

	for d in result:
		ss_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
		if currency == company_currency:
			ss_map[d.parent][d.salary_component] += flt(d.amount) * flt(
				d.exchange_rate if d.exchange_rate else 1
			)
		else:
			ss_map[d.parent][d.salary_component] += flt(d.amount)

	return ss_map


def get_departments(department, company):
	departments_list = get_descendants_of("Department", department)
	departments_list.append(department)
	return departments_list


@frappe.whitelist()
def approve(data: str):
	import json

	from frappe.utils.background_jobs import enqueue

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
			except Exception as e:
				frappe.log_error(e)
