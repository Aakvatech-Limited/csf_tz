# Copyright (c) 2017, Bravo Logisitcs and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class Bond(Document):
	pass


@frappe.whitelist()
def cancel_bond(bond_ref, no_of_packages, cancel_date, cancel_doctype, cancel_docname):
	existing_bond = frappe.get_value("Bond", {"reference_no": bond_ref})
	if existing_bond:
		bond = frappe.get_doc("Bond", existing_bond)
		# Check if it has been cancelled
		existing_cancel_ref = False
		if bond.bond_history:
			for cancel_history in bond.bond_history:
				if (
					cancel_history.reference_doctype == cancel_doctype
					and cancel_history.reference_docname == cancel_docname
				):
					check_total_bundles(bond, no_of_packages, cancel_history.name)
					cancel_history.set("no_of_packages", no_of_packages)
					cancel_history.set("date", cancel_date)
					bond.db_set("bond_history", bond.bond_history)
					existing_cancel_ref = True
		elif not bond.bond_history or not existing_cancel_ref:
			check_total_bundles(bond, no_of_packages)
			new_bond_history = {
				"date": cancel_date,
				"no_of_bundles": no_of_packages,
				"reference_doctype": cancel_doctype,
				"reference_docname": cancel_docname,
			}
			bond.db_set("bond_history", [new_bond_history])


def check_total_bundles(doc, no_of_packages, exclude=None):
	if doc.bond_history:
		total_cancelled = 0
		for cancellation in doc.bond_history:
			if not exclude or (exclude and cancellation.name != exclude):
				total_cancelled = total_cancelled + float(cancellation.no_of_bundles)

		if (total_cancelled + no_of_packages) > doc.no_of_packages:
			frappe.throw(
				"Error: The number of cancelled bond bundles is greater than the number of bundles in the bond."
			)


@frappe.whitelist()
def create_update_bond(**args):
	args = frappe._dict(args)

	existing_bond = frappe.db.get_value("Bond", {"reference_no": args.reference_no})

	# If existing, update value and no of packages information
	if existing_bond:
		doc = frappe.get_doc("Bond", existing_bond)
		doc.db_set("bond_value", args.bond_value)
		doc.db_set("no_of_packages", args.no_of_packages)
		doc.db_set("cargo", args.cargo)
		return doc
	else:
		new_bond = frappe.new_doc("Bond")
		new_bond.update(
			{
				"reference_no": args.reference_no,
				"bond_value": args.bond_value,
				"no_of_packages": args.no_of_packages,
				"cargo": args.cargo,
				"reference_doctype": args.reference_doctype,
				"reference_docname": args.reference_docname,
			}
		)
		new_bond.insert(ignore_permissions=True)
		return new_bond
