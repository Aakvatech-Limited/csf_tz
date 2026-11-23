# Copyright (c) 2022, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmailSalarySlips(Document):
	def on_submit(self):
		self.send_salary_slip_email()

	def send_salary_slip_email(self):
		# Employees selected to send mail
		selected_employees = filter(lambda x: x.send_email, self.employees)
		selected_employees = list(selected_employees)
		employees = []
		for employee in selected_employees:
			employees.append(employee.employee)
		salary_slips = frappe.db.get_list(
			"Salary Slip",
			filters=[["employee", "in", employees], ["payroll_entry", "=", self.payroll_entry]],
			pluck="name",
		)
		if frappe.db.get_single_value("Payroll Settings", "email_salary_slip_to_employee"):
			for ss in salary_slips:
				doc = frappe.get_doc("Salary Slip", ss)
				doc.email_salary_slip()
