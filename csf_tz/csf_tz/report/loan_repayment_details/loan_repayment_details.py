# Copyright (c) 2022, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


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


def get_loans_not_started_to_be_paid(filters, all_repayments):
	conditions = ""
	if filters.get("employee"):
		conditions += " AND l.applicant = '%s' " % filters["employee"]

	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-sql-format-injection
	return frappe.db.sql(
		"""
		SELECT
			l.applicant AS applicant,
			l.applicant_name AS applicant_name,
			GROUP_CONCAT(l.name ORDER BY l.posting_date SEPARATOR ', ') AS loan,
			SUM(l.total_payment) AS total_payable_amount,
			null AS amount_paid_from_salary,
			null AS amount_paid_not_from_salary,
			SUM(wr.write_off_amount) AS write_off_amount,
			null AS loan_balance
		FROM `tabLoan` l
		LEFT JOIN `tabLoan Write Off` wr ON l.name = wr.loan and l.applicant = wr.applicant
		WHERE l.name NOT IN ({})
		AND l.status != "Closed"
		AND l.docstatus = 1 {conditions}
		GROUP BY l.applicant
		ORDER BY l.posting_date, l.applicant
	""".format(
			", ".join(frappe.db.escape(loan.against_loan) for loan in all_repayments), conditions=conditions
		),
		as_dict=True,
	)


def get__paid_loans(filters, repayments, from_salary):
	conditional_columns = ""
	if from_salary:
		conditional_columns += """
			SUM(l.total_amount_paid) AS amount_paid_from_salary,
			null AS amount_paid_not_from_salary,
		"""
	else:
		conditional_columns += """
			null AS amount_paid_from_salary,
			SUM(l.total_amount_paid) AS amount_paid_not_from_salary,
		"""

	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-sql-format-injection
	loans = frappe.db.sql(
		"""
		SELECT
			l.applicant AS applicant,
			l.applicant_name AS applicant_name,
			GROUP_CONCAT(l.name ORDER BY l.posting_date SEPARATOR ', ') AS loan,
			SUM(l.total_payment) AS total_payable_amount,
			{conditional_columns}
			SUM(l.written_off_amount) AS write_off_amount,
			null AS loan_balance
		FROM `tabLoan` l
		WHERE l.name in ({})
		AND l.status != "Closed"
		GROUP BY l.applicant
		ORDER BY l.posting_date, l.applicant
	""".format(
			", ".join(frappe.db.escape(loan.against_loan) for loan in repayments),
			conditional_columns=conditional_columns,
		),
		as_dict=True,
	)

	return loans


def get_repayments(filters):
	employee = None
	if filters.get("employee"):
		employee = filters["employee"]
	else:
		employee = ["!=", ""]

	repayments_from_salaries = frappe.get_all(
		"Loan Repayment",
		filters={"loan_type": "Staff Loan", "repay_from_salary": 1, "docstatus": 1, "applicant": employee},
		fields=["against_loan"],
		order_by="posting_date",
		distinct=True,
	)

	repayments_not_from_salaries = frappe.get_all(
		"Loan Repayment",
		filters={"loan_type": "Staff Loan", "repay_from_salary": 0, "docstatus": 1, "applicant": employee},
		fields=["against_loan"],
		order_by="posting_date",
		distinct=True,
	)

	all_repayments = repayments_from_salaries + repayments_not_from_salaries

	return repayments_from_salaries, repayments_not_from_salaries, all_repayments


def get_custom_loan_repayment_not_from_salary(filters):
	return frappe.db.sql(
		"""
		SELECT loan, SUM(payment_amount) AS amount_paid_not_from_salary
		FROM `tabLoan Repayment Not From Salary`
		WHERE loan != ""
		GROUP BY loan
	""",
		as_dict=True,
	)
