import json

import frappe


def get_json():
	# Preserve the original UNION ALL behavior: a DocType may occur in both sets.
	doc_list = []
	for doctype_field, reference_field in (("DocField", "parent"), ("Custom Field", "dt")):
		linked_doctypes = frappe.get_all(
			doctype_field,
			filters={"fieldtype": "Link", "options": ["is", "set"]},
			fields=[reference_field],
			group_by=reference_field,
		)
		for linked in linked_doctypes:
			doctype_name = linked.get(reference_field)
			module = frappe.db.get_value("DocType", doctype_name, "module")
			if module is None:
				continue
			doc_list.append(
			frappe._dict({
				"name": ".".join(("erpnext", module, doctype_name)),
				"doctype_name": doctype_name,
			})
		)

	for doc in doc_list:
		docfield_list = frappe.get_all(
			"DocField",
			filters={"parent": doc.doctype_name, "fieldtype": "Link"},
			fields="options",
			group_by="options",
		)
		custom_field_list = frappe.get_all(
			"Custom Field",
			filters={"dt": doc.doctype_name, "fieldtype": "Link"},
			fields="options",
			group_by="options",
		)
		doc["imports"] = []
		for options in docfield_list:
			options_string = (
				"erpnext."
				+ frappe.get_value("DocType", doc.doctype_name, "module")
				+ "."
				+ options.get("options")
			)
			doc["imports"].append(options_string)
		for options in custom_field_list:
			options_string = (
				"erpnext."
				+ frappe.get_value("DocType", doc.doctype_name, "module")
				+ "."
				+ options.get("options")
			)
			doc["imports"].append(options_string)

	return json.dumps(doc_list)
