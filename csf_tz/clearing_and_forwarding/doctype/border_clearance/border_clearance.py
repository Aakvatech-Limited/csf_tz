# Copyright (c) 2017, Bravo Logisitcs and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

from csf_tz.after_sales_services.doctype.requested_payments.requested_payments import (
	validate_requested_funds,
)


class BorderClearance(Document):
	from csf_tz.after_sales_services.doctype.reference_payment_table.reference_payment_table import (
		update_child_table,
	)

	def onload(self):
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default(
				"company"
			)

	def before_save(self):
		validate_requested_funds(self)


@frappe.whitelist()
def create_border_clearance(**args):
	args = frappe._dict(args)

	existing_border_clearance = frappe.db.get_value("Border Clearance", {"file_number": args.file_number})

	if existing_border_clearance:
		doc = frappe.get_doc("Border Clearance", existing_border_clearance)
		doc.db_set("no_of_borders", args.number_of_borders)
		doc.db_set("location", args.location)
		doc.db_set("documents_received", args.documents_received_date)
		doc.db_set("client", args.customer)
		return existing_border_clearance
	else:
		new_border_clearance = frappe.new_doc("Border Clearance")
		new_border_clearance.update(
			{
				"no_of_borders": args.number_of_borders,
				"location": args.location,
				"documents_received": args.documents_received_date,
				"client": args.customer,
				"file_number": args.file_number,
			}
		)
		new_border_clearance.insert(ignore_permissions=True)
		return new_border_clearance.name


@frappe.whitelist()
def check_existing(**args):
	args = frappe._dict(args)

	existing_clearance = frappe.db.get_value(
		"Border Clearance",
		{
			"trip_reference_no": args.trip_reference,
			"main_return_select": args.main_return_select,
		},
	)

	if existing_clearance:
		return "Exists"
	else:
		return "Not Exist"
