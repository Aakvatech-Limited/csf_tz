# Copyright (c) 2022, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not frappe.db.exists("DocType", "Loan Repayment"):
		frappe.throw(_("The Lending app is not installed on this site"))

	loans = []
	data = []
	columns = get_columns(filters)

	repayments_from_salaries, repayments_not_from_salaries, all_repayments = get_repayments(filters)

	if repayments_from_salaries:
		loans += get__paid_loans(filters, repayments_from_salaries, True)

	if repayments_not_from_salaries:
		loans += get__paid_loans(filters, repayments_not_from_salaries, False)

	if all_repayments:
		loans += get_loans_not_started_to_be_paid(filters, all_repayments)

	custom_loan_repayment_records = get_custom_loan_repayment_not_from_salary(filters)

	for loan in loans:
		for custom_loan_repayment in custom_loan_repayment_records:
			if custom_loan_repayment.loan in loan.loan:
				loan.amount_paid_not_from_salary += flt(custom_loan_repayment.amount_paid_not_from_salary)

		loan.update(
			{
				"loan_balance": flt(loan.total_payable_amount)
				- flt(loan.amount_paid_from_salary)
				- flt(loan.amount_paid_not_from_salary)
				- flt(loan.write_off_amount)
			}
		)
		data.append(loan)

	return columns, data


def get_columns(filters):
	return [
		{"fieldname": "applicant", "fieldtype": "Data", "label": _("Applicant"), "width": "150px"},
		{"fieldname": "applicant_name", "fieldtype": "Data", "label": _("Applicant Name"), "width": "150px"},
		{"fieldname": "loan", "fieldtype": "Data", "label": _("Loan"), "width": "100px"},
		{
			"fieldname": "total_payable_amount",
			"fieldtype": "Currency",
			"label": _("Total Payable Amount"),
			"width": "150px",
		},
		{
			"fieldname": "amount_paid_from_salary",
			"fieldtype": "Currency",
			"label": _("Amount Paid From Salary"),
			"width": "150px",
		},
		{
			"fieldname": "amount_paid_not_from_salary",
			"fieldtype": "Currency",
			"label": _("Amount Paid not From Salary"),
			"width": "150px",
		},
		{
			"fieldname": "write_off_amount",
			"fieldtype": "Currency",
			"label": _("Write Off Amount"),
			"width": "150px",
		},
		{"fieldname": "loan_balance", "fieldtype": "Currency", "label": _("Loan Balance"), "width": "150px"},
	]


def _loan_summary_query(loan_names, filters=None, unpaid=False, from_salary=False):
	from frappe.query_builder.functions import GroupConcat, Sum

	loan = frappe.qb.DocType("Loan")
	query = frappe.qb.from_(loan)
	if unpaid:
		write_off = frappe.qb.DocType("Loan Write Off")
		query = query.left_join(write_off).on(
			(write_off.loan == loan.name) & (write_off.applicant == loan.applicant)
		)
		write_off_total = Sum(write_off.write_off_amount)
	else:
		write_off_total = Sum(loan.written_off_amount)

	query = (
		query.select(
			loan.applicant.as_("applicant"),
			loan.applicant_name.as_("applicant_name"),
			GroupConcat(loan.name).orderby(loan.posting_date).separator(", ").as_("loan"),
			Sum(loan.total_payment).as_("total_payable_amount"),
			write_off_total.as_("write_off_amount"),
		)
		.where(loan.status != "Closed")
		.groupby(loan.applicant)
		.orderby(loan.posting_date)
		.orderby(loan.applicant)
	)
	if unpaid:
		query = query.where(loan.docstatus == 1)
		if filters and filters.get("employee"):
			query = query.where(loan.applicant == filters["employee"])
		query = query.where(loan.name.notin(loan_names)) if loan_names else query
		query = query.select(
			frappe.qb.terms.NullValue().as_("amount_paid_from_salary"),
			frappe.qb.terms.NullValue().as_("amount_paid_not_from_salary"),
		)
	elif from_salary:
		query = query.select(
			Sum(loan.total_amount_paid).as_("amount_paid_from_salary"),
			frappe.qb.terms.NullValue().as_("amount_paid_not_from_salary"),
		)
	else:
		query = query.select(
			frappe.qb.terms.NullValue().as_("amount_paid_from_salary"),
			Sum(loan.total_amount_paid).as_("amount_paid_not_from_salary"),
		)
	if not unpaid:
		query = query.where(loan.name.isin(loan_names))
	return query.run(as_dict=True)


def get_loans_not_started_to_be_paid(filters, all_repayments):
	return _loan_summary_query(
		[entry.against_loan for entry in all_repayments], filters=filters, unpaid=True
	)


def get__paid_loans(filters, repayments, from_salary):
	return _loan_summary_query(
		[entry.against_loan for entry in repayments], from_salary=from_salary
	)
def get_custom_loan_repayment_not_from_salary(filters):
	from frappe.query_builder.functions import Sum

	repayment = frappe.qb.DocType("Loan Repayment Not From Salary")
	return (
		frappe.qb.from_(repayment)
		.select(repayment.loan, Sum(repayment.payment_amount).as_("amount_paid_not_from_salary"))
		.where(repayment.loan != "")
		.groupby(repayment.loan)
		.run(as_dict=True)
	)
