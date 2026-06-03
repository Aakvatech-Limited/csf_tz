from __future__ import unicode_literals

import frappe


def execute():
	frappe.db.sql(
		"""
          update `tabSalary Slip` ss
          inner join `tabEmployee` e ON ss.employee = e.name
          set ss.payroll_cost_center = e.payroll_cost_center where ss.payroll_cost_center IS NULL
        """
	)
