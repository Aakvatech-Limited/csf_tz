# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.desk.query_report import add_total_row
from frappe.query_builder.functions import Count, Sum

def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "technician",
			"label": _("Technician"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150
		},
		{
			"fieldname": "employee_name",
			"label": _("Technician Name"),
			"fieldtype": "Data",
			"width": 150,
			"hidden": True
		},
		{
			"fieldname": "workshop",
			"label": _("Workshop"),
			"fieldtype": "link",
			"options": "Warehouse",
			"width": 150
		},
		{
			"fieldname": "no_of_jobs_completed",
			"label": _("No of Jobs Completed"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "total_billable_hours",
			"label": _("Total Billable Hours"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "total_standard_hours",
			"label": _("Standard Hours"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "total_work_value",
			"label": _("Total Work Value"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "job_efficiency",
			"label": _("Technician Efficiency (%)"),
			"fieldtype": "Float",
			"width": 150
		},
	]

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))

	maintenance_services_table = frappe.qb.DocType("Maintenance Services Table")
	job_card = frappe.qb.DocType("Job Card")
	employee = frappe.qb.DocType("Employee")
	query = (
		frappe.qb.from_(maintenance_services_table)
		.left_join(job_card)
		.on(maintenance_services_table.parent == job_card.name)
		.left_join(employee)
		.on(employee.name == maintenance_services_table.technician)
		.select(
			maintenance_services_table.technician,
			employee.employee_name,
			job_card.warehouse.as_("workshop"),
			Count(maintenance_services_table.name).as_("no_of_jobs_completed"),
			Sum(maintenance_services_table.billable_hours).as_("total_billable_hours"),
			Sum(maintenance_services_table.standard_hours).as_("total_standard_hours"),
			Sum(maintenance_services_table.standard_cost * maintenance_services_table.billable_hours).as_("total_work_value"),
			(
				(Sum(maintenance_services_table.billable_hours) / Sum(maintenance_services_table.standard_hours)) * 100
			).as_("job_efficiency"),
		)
		.where(maintenance_services_table.start_date[filters.from_date:filters.to_date])
		.where(job_card.docstatus == 1)
		.where(maintenance_services_table.service_status == 'Fully Completed')
		.groupby(maintenance_services_table.technician, job_card.warehouse)
	)

	if filters.workshop:
		query = query.where(job_card.warehouse == filters.workshop)
		
	if filters.technician:
		query = query.where(maintenance_services_table.technician == filters.technician)

	data = query.run(as_list=1)
	return columns, data
