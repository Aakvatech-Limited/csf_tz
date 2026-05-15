from __future__ import unicode_literals

from erpnext.payroll.doctype.salary_slip.salary_slip import SalarySlip

# from erpnext.payroll.doctype.additional_salary.additional_salary import get_additional_salary_component


class csftz_SalarySlip(SalarySlip):
	# def add_additional_salary_components(self, component_type):
	#     salary_components_details, additional_salary_details = get_additional_salary_component(self.employee, self.start_date, self.end_date, component_type)
	#     if salary_components_details and additional_salary_details:
	#         for additional_salary in additional_salary_details:
	#             additional_salary = frappe._dict(additional_salary)
	#             # exit if additional_salary.name already exists in self.earnings/deductions
	#             existing_additional_salary_record_found = 0
	#             for d in self.get(component_type):
	#                 if d.additional_salary == additional_salary.name:
	#                     existing_additional_salary_record_found = 1
	#                     break
	#             if existing_additional_salary_record_found:
	#                 continue
	#             amount = additional_salary.amount
	#             overwrite = additional_salary.overwrite
	#             self.update_component_row(frappe._dict(salary_components_details[additional_salary.component]), amount, component_type, overwrite=overwrite, additional_salary=additional_salary.name)
	pass
