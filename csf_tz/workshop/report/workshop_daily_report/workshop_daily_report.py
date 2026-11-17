# Copyright (c) 2013, Bravo Logistics and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Concat, Replace
from csf_tz.utils.query_builder import get_latest_reporting_status_query
import ast
import datetime
from datetime import date

def execute(filters=None):
	columns, data = [], []
	
	columns = [
		{
			"fieldname": "reference",
			"label": _("Job Card Reference"),
			"fieldtype": "Link",
			"options": "Job Card",
			"width": 100
		},
		{
			"fieldname": "requested_on",
			"label": _("Requested On"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "started_on",
			"label": _("Started Work On"),
			"fieldtype": "Datetime",
			"width": 100
		},
		{
			"fieldname": "ended_on",
			"label": _("Ended On"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "days_in_workshop",
			"label": _("Days in Workshop"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "job_type",
			"label": _("Job Type"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "work_done_on",
			"label": _("Work Done On"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "plate_number",
			"label": _("Plate NUmber"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "fleet_number",
			"label": _("Fleet NUmber"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "job_description",
			"label": _("Job Description"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "reporting_status",
			"label": _("Reporting Status"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 150
		}
	]
	
	today = datetime.date.today().strftime("%Y-%m-%d")
	
	job_card = frappe.qb.DocType("Job Card")
	workshop_request = frappe.qb.DocType("Workshop Request")
	trailer = frappe.qb.DocType("Trailer")
	vehicle = frappe.qb.DocType("Vehicle")

	data = (
		frappe.qb.from_(job_card)
		.left_join(workshop_request)
		.on(workshop_request.name == job_card.requested_from)
		.left_join(trailer)
		.on((trailer.name == job_card.job_done_on_docname) & (job_card.job_done_on == 'Trailer'))
		.left_join(vehicle)
		.on((vehicle.name == job_card.job_done_on_docname) & (job_card.job_done_on == 'Vehicle'))
		.select(
			job_card.name.as_("reference"),
			workshop_request.requested_date.as_("requested_on"),
			job_card.start_date,
			job_card.end_date,
			Concat(job_card.start_date, ' ', job_card.start_time).as_("started_on"),
			Concat(job_card.end_date, ' ', job_card.end_time).as_("ended_on"),
			job_card.job_type,
			job_card.job_done_on.as_("work_done_on"),
			Case()
			.when(job_card.job_done_on == 'Vehicle', job_card.job_done_on_docname)
			.when(job_card.job_done_on == 'Trailer', trailer.number_plate)
			.as_("plate_number"),
			Case().when(job_card.job_done_on == 'Vehicle', vehicle.fleet_number).else_('').as_("fleet_number"),
			Replace(Concat(job_card.job_type, ' ', job_card.job_description), '\n', '. ').as_("job_description"),
			get_latest_reporting_status_query(job_card.name, "Job Card").as_("reporting_status"),
			job_card.status,
		)
		.where(
			((job_card.docstatus != 2) & (job_card.status == 'Open'))
			| ((job_card.status == 'Closed') & (job_card.end_date == today))
		)
	).run(as_dict=1)
						 
	for row in data:
		if row.start_date and row.end_date:
			row.update({"days_in_workshop": (row.end_date - row.start_date).days})
		elif row.start_date and not row.end_date:
			row.update({"days_in_workshop": (datetime.date.today() - row.start_date).days})
						 
	return columns, data
