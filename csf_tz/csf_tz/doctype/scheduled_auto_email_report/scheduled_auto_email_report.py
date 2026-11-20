# Copyright (c) 2023, Aakvatech Limited and contributors
# For license information, please see license.txt

import datetime

import frappe
from frappe.model.document import Document


class ScheduledAutoEmailReport(Document):
	def validate(self):
		if self.schedule == "Monthly" and (self.day_of_month < 1 or self.day_of_month > 28):
			frappe.throw("Invalid day of month. The Day of Month should be between 1 and 28.")
		elif self.schedule != "Monthly":
			self.day_of_month = None


def get_report_list():
	day_of_month = datetime.datetime.today().day
	day_of_week = datetime.datetime.today().strftime("%A")
	current_time = datetime.datetime.now()
	start_time = current_time - datetime.timedelta(seconds=300)
	end_time = current_time + datetime.timedelta(seconds=5)
	scheduled_list = frappe.get_all(
		"Scheduled Auto Email Report",
		filters=[
			["enabled", "=", 1],
			["schedule_time", ">", str(start_time)],
			["schedule_time", "<", str(end_time)],
			["schedule", "=", "Daily"],
		],
	)
	scheduled_list += frappe.get_all(
		"Scheduled Auto Email Report",
		filters=[
			["enabled", "=", 1],
			["schedule_time", ">", str(start_time)],
			["schedule_time", "<", str(end_time)],
			["schedule", "=", "Monthly"],
			["day_of_month", "=", day_of_month],
		],
	)
	scheduled_list += frappe.get_all(
		"Scheduled Auto Email Report",
		filters=[
			["enabled", "=", 1],
			["schedule_time", ">", str(start_time)],
			["schedule_time", "<", str(end_time)],
			["schedule", "=", day_of_week],
		],
	)

	return scheduled_list


def send_report():
	report_list = get_report_list()
	for report in report_list:
		report_doc = frappe.get_doc("Auto Email Report", report.name)
		report_doc.send()
