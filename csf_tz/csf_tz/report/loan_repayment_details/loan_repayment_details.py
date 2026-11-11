# Copyright (c) 2022, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt
from pypika.terms import ValueWrapper
from csf_tz.utils.query_builder import GroupConcatWithSeparator


def execute(filters=None):
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
		
		loan.update({
			"loan_balance": flt(loan.total_payable_amount) - flt(loan.amount_paid_from_salary) - flt(loan.amount_paid_not_from_salary) - flt(loan.write_off_amount)
		})
		data.append(loan)

	return columns, data

def get_columns(filters):
	return [
		{"fieldname": "applicant", "fieldtype": "Data", "label": _("Applicant"), "width": "150px"},
		{"fieldname": "applicant_name", "fieldtype": "Data", "label": _("Applicant Name"), "width": "150px"},
		{"fieldname": "loan", "fieldtype": "Data", "label": _("Loan"), "width": "100px"},
		{"fieldname": "total_payable_amount", "fieldtype": "Currency", "label": _("Total Payable Amount"), "width": "150px"},
		{"fieldname": "amount_paid_from_salary", "fieldtype": "Currency", "label": _("Amount Paid From Salary"), "width": "150px"},
		{"fieldname": "amount_paid_not_from_salary", "fieldtype": "Currency", "label": _("Amount Paid not From Salary"), "width": "150px"},
		{"fieldname": "write_off_amount", "fieldtype": "Currency", "label": _("Write Off Amount"), "width": "150px"},
		{"fieldname": "loan_balance", "fieldtype": "Currency", "label": _("Loan Balance"), "width": "150px"},
	]


def get_loans_not_started_to_be_paid(filters, all_repayments):
	loan = frappe.qb.DocType("Loan")
	loan_write_off = frappe.qb.DocType("Loan Write Off")

	query = (
		get_loan_summary_query(
			frappe.qb.from_(loan)
			.left_join(loan_write_off)
			.on((loan.name == loan_write_off.loan) & (loan.applicant == loan_write_off.applicant)),
			loan,
			ValueWrapper(None),
			ValueWrapper(None),
			Sum(loan_write_off.write_off_amount),
		)
		.where(loan.name.notin([repayment.against_loan for repayment in all_repayments]))
		.where(loan.status != "Closed")
		.where(loan.docstatus == 1)
	)

	if filters.get("employee"):
		query = query.where(loan.applicant == filters["employee"])

	return query.run(as_dict=True)


def get__paid_loans(filters, repayments, from_salary):
	loan = frappe.qb.DocType("Loan")
	amount_paid = Sum(loan.total_amount_paid)

	if from_salary:
		amount_paid_from_salary = amount_paid
		amount_paid_not_from_salary = ValueWrapper(None)
	else:
		amount_paid_from_salary = ValueWrapper(None)
		amount_paid_not_from_salary = amount_paid

	loans = (
		get_loan_summary_query(
			frappe.qb.from_(loan),
			loan,
			amount_paid_from_salary,
			amount_paid_not_from_salary,
			Sum(loan.written_off_amount),
		)
		.where(loan.name.isin([repayment.against_loan for repayment in repayments]))
		.where(loan.status != "Closed")
		.run(as_dict=True)
	)

	return loans


def get_loan_summary_query(query, loan, amount_paid_from_salary, amount_paid_not_from_salary, write_off_amount):
	"""Loans grouped per applicant with the report's summary columns."""
	return (
		query.select(
			loan.applicant,
			loan.applicant_name,
			GroupConcatWithSeparator(loan.name, ", ", order_by=loan.posting_date).as_("loan"),
			Sum(loan.total_payment).as_("total_payable_amount"),
			amount_paid_from_salary.as_("amount_paid_from_salary"),
			amount_paid_not_from_salary.as_("amount_paid_not_from_salary"),
			write_off_amount.as_("write_off_amount"),
			ValueWrapper(None).as_("loan_balance"),
		)
		.groupby(loan.applicant)
		.orderby(loan.posting_date)
		.orderby(loan.applicant)
	)


def get_repayments(filters):
	employee = None
	if filters.get("employee"):
		employee = filters["employee"]
	else:
		employee = ["!=", ""]

	repayments_from_salaries = frappe.get_all("Loan Repayment", 
		filters={"loan_type": "Staff Loan", "repay_from_salary": 1, "docstatus": 1, "applicant": employee},
		fields=["Distinct(against_loan) as against_loan"],
		order_by="posting_date"
	)

	repayments_not_from_salaries = frappe.get_all("Loan Repayment", 
		filters={"loan_type": "Staff Loan", "repay_from_salary": 0, "docstatus": 1, "applicant": employee},
		fields=["Distinct(against_loan) as against_loan"],
		order_by="posting_date"
	)
	
	all_repayments = repayments_from_salaries + repayments_not_from_salaries

	return repayments_from_salaries, repayments_not_from_salaries, all_repayments


def get_custom_loan_repayment_not_from_salary(filters):
	loan_repayment = frappe.qb.DocType("Loan Repayment Not From Salary")
	return (
		frappe.qb.from_(loan_repayment)
		.select(loan_repayment.loan, Sum(loan_repayment.payment_amount).as_("amount_paid_not_from_salary"))
		.where(loan_repayment.loan != "")
		.groupby(loan_repayment.loan)
		.run(as_dict=True)
	)
