import json
import os

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

folder = "../patches/property_setter/property_setter_json"


def load_json(file):
	# These maintenance helpers only load bundled JSON fixtures.
	if not isinstance(file, str) or not file.endswith(".json") or os.path.basename(file) != file:
		raise ValueError("Expected a JSON filename from the bundled fixtures directory")
	base_directory = os.path.realpath(os.path.join(os.path.dirname(__file__), folder))
	json_file_path = os.path.realpath(os.path.join(base_directory, file))
	if os.path.commonpath([base_directory, json_file_path]) != base_directory:
		raise ValueError("Fixture path escapes its directory")
	with open(json_file_path, encoding="utf-8") as source:
		return json.load(source)


def create_property_setter_from_json(property_setters_obj):
	disallowed_fields = [
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"is_system_generated",
		"__last_sync_on",
	]

	existing_setters = {
		d.name for d in frappe.db.get_all("Property Setter", fields=["name"], page_length=10000)
	}

	for property_setter in property_setters_obj:
		if property_setter.get("name") in existing_setters:
			continue

		if not frappe.db.exists("DocType", property_setter.get("doc_type")):
			continue

		if property_setter.get("doctype_or_field") == "DocType":
			for_doctype = True
		else:
			for_doctype = False

		all_fields = frappe.get_meta("Property Setter").get_valid_columns()
		field_list = set(all_fields).difference(disallowed_fields)

		property_setter_dict = {
			field: property_setter.get(field) for field in field_list if field in property_setter
		}

		make_property_setter(
			doctype=property_setter_dict["doc_type"],
			fieldname=property_setter_dict.get("field_name", None),
			property=property_setter_dict["property"],
			value=property_setter_dict["value"],
			property_type=property_setter_dict["property_type"],
			for_doctype=for_doctype,
			validate_fields_for_doctype=False,
		)


def execute():
	# read names of only json files in this folder and put it into files list
	files = list(
		filter(
			lambda x: x.endswith(".json"),
			os.listdir(os.path.join(os.path.abspath(os.path.dirname(__file__)), folder)),
		)
	)
	for file in files:
		data = load_json(file)
		create_property_setter_from_json(data)
