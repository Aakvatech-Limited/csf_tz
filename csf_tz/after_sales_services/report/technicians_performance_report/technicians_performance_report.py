# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.desk.query_report import add_total_row
from frappe.query_builder import Criterion
from csf_tz.utils.query_builder import get_match_criterion
import datetime

def execute(filters=None):
	return _execute(filters)

def _execute(filters=None, additional_table_columns=None, additional_query_columns=None):
	if not filters: filters = {}
	columns = get_columns(additional_table_columns)
	item_list = get_items(filters)

	data = []
	for d in item_list:
		#For actual hours time calculation = date difference in hours + time difference. There may be a simpler way to do it but ......
		time_difference = 0
		if d.end_date == d.start_date:
			time_difference = (d.end_time.seconds - d.start_time.seconds) / 3600
		else:
			time_difference = ((86400 - d.start_time.seconds) + d.end_time.seconds) / 3600
		date_difference = (d.end_date - d.start_date).total_seconds() / 3600
		actual_hrs = date_difference + time_difference
		
		service_value = d.billable_hours * d.standard_cost
		hrs_difference = actual_hrs - d.standard_hours
		row = [d.name, d.technician, d.employee_name, d.start_date, d.start_time, d.end_date, d.end_time, d.service, d.standard_hours, 
				actual_hrs, hrs_difference, d.billable_hours, d.standard_cost, service_value, d.warehouse, d.customer]
		data.append(row)
	return columns, data

def get_columns(additional_table_columns):
	columns = [
		_("Job Card") + ":Link/Job Card:120",
		_("Technician") + ":Link/User:100",
		_("Technician Name") + ":Data:100",
		_("Start Date") + ":Date:80",
		_("Start Time") + ":Time:80", 
		_("End Date") + ":Date:80",
		_("End Time") + ":Time:80",
		_("Service") + ":Link/Maintenance Service:120",
		_("Standard Hrs") + ":Float:120",
		_("Actual Hrs") + ":Float:120",
		_("Hrs Difference") + ":Float:120",
		_("Billable Hrs") + ":Float:120",
		_("Standard Rate") + ":Currency/currency:120",
		_("Service Value") + ":Currency/currency:120",
		_("Warehouse") + ":Link/Warehouse:120",
		_("Customer") + ":Link/Customer:120"]

	return columns

def get_conditions(filters, job_card, maintenance_services_table):
	conditions = []
	if filters.get("custm"):
		conditions.append(job_card.customer == filters.get("custm"))
	if filters.get("workshop"):
		conditions.append(job_card.warehouse == filters.get("workshop"))
	if filters.get("user"):
		conditions.append(maintenance_services_table.technician == filters.get("user"))
	if filters.get("from_date"):
		conditions.append(maintenance_services_table.start_date >= filters.get("from_date"))
	if filters.get("to_date"):
		conditions.append(maintenance_services_table.start_date <= filters.get("to_date"))
	return conditions

def get_items(filters):
	job_card = frappe.qb.DocType("Job Card")
	maintenance_services_table = frappe.qb.DocType("Maintenance Services Table")
	employee = frappe.qb.DocType("Employee")
	conditions = get_conditions(filters, job_card, maintenance_services_table)
	match_criterion = get_match_criterion("Job Card")

	query = (
		frappe.qb.from_(job_card)
		.from_(maintenance_services_table)
		.left_join(employee)
		.on(employee.name == maintenance_services_table.technician)
		.select(
			job_card.name,
			maintenance_services_table.start_date,
			maintenance_services_table.end_date,
			maintenance_services_table.start_time,
			maintenance_services_table.end_time,
			job_card.name,
			job_card.customer,
			job_card.status,
			job_card.warehouse,
			employee.employee_name,
			maintenance_services_table.service,
			maintenance_services_table.billable_hours,
			maintenance_services_table.standard_hours,
			maintenance_services_table.technician,
			maintenance_services_table.standard_cost,
		)
		.where(job_card.name == maintenance_services_table.parent)
		.where(job_card.docstatus == 1)
		.where(Criterion.all(conditions))
		.orderby(maintenance_services_table.start_date)
	)

	if match_criterion:
		query = query.where(match_criterion)

	return query.run(as_dict=1)
