# Copyright (c) 2015, Bravo Logisitcs and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

from csf_tz.after_sales_services.doctype.requested_payments.requested_payments import (
	validate_requested_funds,
)
from csf_tz.clearing_and_forwarding.doctype.bond.bond import create_update_bond


class Import(Document):
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

		if self.cargo_information:
			for cargo in self.cargo_information:
				if cargo.get("bond_ref_no") and cargo.get("bond_value"):
					create_update_bond(
						reference_no=cargo.bond_ref_no,
						bond_value=cargo.bond_value,
						no_of_packages=cargo.no_of_packages,
						cargo=self.cargo,
						reference_doctype="Import",
						reference_docname=self.name,
					)


@frappe.whitelist()
def create_import(**args):
	args = frappe._dict(args)

	existing_import = frappe.db.get_value("Import", {"bl_number": args.bl_number})

	if existing_import:
		doc = frappe.get_doc("Import", existing_import)
		doc.db_set("reference_file_number", args.file_number)
		doc.db_set("import_type", args.import_type)
		return existing_import
	else:
		new_import = frappe.new_doc("Import")
		new_import.update(
			{
				"bl_number": args.bl_number,
				"documents_received_date": args.documents_received_date,
				"location": args.location,
				"customer": args.customer,
				"reference_file_number": args.file_number,
				"import_type": args.import_type,
			}
		)
		new_import.insert(ignore_permissions=True)
		return new_import.name


@frappe.whitelist()
def check_import_status(**args):
	args = frappe._dict(args)
	# get import
	existing_import = frappe.db.get_value("Import", {"reference_file_number": args.file_number})
	if existing_import:
		doc = frappe.get_doc("Import", existing_import)
		status = doc.status
		if status == "Open":
			frappe.msgprint(
				"Cannot Close the File because it's IMPORT is not closed,Please Close the IMPORT first"
			)
