from __future__ import unicode_literals

import json

import frappe


@frappe.whitelist()
def get_job_cards():
	data = frappe.get_list(
		"Job Card",
		filters={
			"status": ["in", ["Open", "Work In Progress", "Material Transferred", "On Hold", "Submitted"]],
			"docstatus": 0,
		},
		fields=["*"],
		limit_page_length=0,
		order_by="name",
	)
	for card in data:
		card["operation"] = frappe.get_doc("Operation", card.operation)
		card["work_order_image"] = frappe.get_value("Work Order", card.work_order, "image")
		card["time_logs"] = frappe.get_all("Job Card Time Log", filters={"parent": card.name}, fields=["*"])
	return data


@frappe.whitelist()
def get_employees(company: str):
	data = frappe.get_list(
		"Employee",
		filters={"status": "Active", "company": company},
		fields=["name", "employee_name"],
		limit_page_length=0,
		order_by="name",
	)

	return data


@frappe.whitelist()
def save_doc(doc: str, action: str = "Save"):
	doc = json.loads(doc)
	cur_doc = frappe.get_doc("Job Card", doc.get("name"))
	cur_doc.update(doc)
	cur_doc.save()
	if action == "Submit":
		cur_doc.submit()
	return cur_doc
