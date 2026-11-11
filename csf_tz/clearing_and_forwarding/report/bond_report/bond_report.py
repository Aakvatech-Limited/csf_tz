# Copyright (c) 2013, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.query_builder import Criterion, Field
from frappe.query_builder.custom import ConstantColumn

def execute(filters=None):
	columns, data = [], []
	
	columns = [
		{
			"fieldname": "bond_reference",
			"label": _("Bond Reference"),
			"fieldtype": "Data",
			"width": 150
		},
		{
            "fieldname":"sub_t1",
            "label": _("Sub T1"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname":"bond_date",
            "label": _("Bond Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname":"bond_value",
            "label": _("Bond Value"),
            "fieldtype": "Float",
            "width": 150
        },
        {
            "fieldname":"cargo",
            "label": _("Cargo"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname":"bond_cancellation_date",
            "label": _("Bond Cancelled"),
            "fieldtype": "Date",
            "width": 150
        },
        {
            "fieldname":"reference_type",
            "label": _("Reference Type"),
            "fieldtype": "Link",
            "options": "Doctype",
            "width": 100
        },
        {
            "fieldname":"reference_doc",
            "label": _("Reference"),
            "fieldtype": "Dynamic Link",
            "options": "reference_type",
            "width": 100
        }
	]
	
	conditions = []
	
	if filters:
		if filters.from_date > filters.to_date:
			frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))
			
		conditions = get_conditions(filters)
	
	bonds = get_bonds_query().as_("a")
	query = frappe.qb.from_(bonds).select("*").where(Criterion.all(conditions)).orderby(Field("bond_date"))
	data = query.run(as_dict=True)
	return columns, data


def get_conditions(filters):
	conditions = []
	if filters.from_date and filters.to_date:
		if filters.filter_by == 'Bond Date':
			conditions += [Field("bond_date") >= filters.from_date, Field("bond_date") <= filters.to_date]
		elif filters.filter_by == 'Bond Cancelation Date':
			conditions += [Field("bond_cancellation_date") >= filters.from_date, Field("bond_cancellation_date") <= filters.to_date]

	if filters.bt:
		conditions.append(Field("bond_reference").like(filters.bt))

	if filters.status == 'Not Cancelled':
		conditions.append(Field("bond_cancellation_date").isnull())
	elif filters.status == 'Cancelled':
		conditions.append(Field("bond_cancellation_date").isnotnull())
	return conditions


def get_bonds_query():
	return get_import_bonds_query() * get_export_bonds_query() * get_border_container_bonds_query() * get_border_loose_bonds_query()


def get_import_bonds_query():
	cargo = frappe.qb.DocType("Cargo Details").as_("cargo1")
	border_cargo = frappe.qb.DocType("Cargo Details").as_("cargo2")
	import_doc = frappe.qb.DocType("Import")
	border_clearance = frappe.qb.DocType("Border Clearance")
	first_border_clearance = (
		frappe.qb.from_(border_cargo)
		.select(border_cargo.parent)
		.where(border_cargo.parenttype == 'Border Clearance')
		.where(border_cargo.bond_ref_no == cargo.bond_ref_no)
		.limit(1)
	)
	return (
		frappe.qb.from_(cargo)
		.left_join(import_doc).on(import_doc.name == cargo.parent)
		.left_join(border_clearance).on(border_clearance.name == first_border_clearance)
		.select(
			import_doc.bt_number.as_("bond_reference"),
			cargo.bond_ref_no.as_("sub_t1"),
			import_doc.t1_approved.as_("bond_date"),
			cargo.bond_value,
			import_doc.cargo,
			border_clearance.bond_canceled_date.as_("bond_cancellation_date"),
			ConstantColumn('Import').as_("reference_type"),
			import_doc.name.as_("reference_doc"),
		)
		.where(cargo.parenttype == 'Import')
		.where(import_doc.bt_number.isnotnull())
		.where(import_doc.bt_number != '')
	)


def get_export_bonds_query():
	bond_reference = frappe.qb.DocType("Bond Reference Table")
	export = frappe.qb.DocType("Export")
	return (
		frappe.qb.from_(bond_reference)
		.left_join(export).on(export.name == bond_reference.parent)
		.select(
			export.bt_ref_no.as_("bond_reference"),
			bond_reference.customs_ref_number.as_("sub_t1"),
			export.bt_approval_date.as_("bond_date"),
			bond_reference.bond_value,
			export.material.as_("cargo"),
			export.bond_validated.as_("bond_cancellation_date"),
			ConstantColumn('Export').as_("reference_type"),
			export.name.as_("reference_doc"),
		)
		.where(bond_reference.parenttype == 'Export')
		.where(export.bt_ref_no.isnotnull())
		.where(export.bt_ref_no != '')
	)


def get_border_container_bonds_query():
	cargo = frappe.qb.DocType("Cargo Details")
	border_clearance = frappe.qb.DocType("Border Clearance")
	return (
		frappe.qb.from_(cargo)
		.left_join(border_clearance).on(border_clearance.name == cargo.parent)
		.select(
			border_clearance.bond_ref_no.as_("bond_reference"),
			cargo.bond_ref_no.as_("sub_t1"),
			border_clearance.bt_approval_date.as_("bond_date"),
			cargo.bond_value,
			border_clearance.cargo_description.as_("cargo"),
			border_clearance.bond_canceled_date.as_("bond_cancellation_date"),
			ConstantColumn('Border Clearance').as_("reference_type"),
			border_clearance.name.as_("reference_doc"),
		)
		.where(cargo.parenttype == 'Border Clearance')
		.where(border_clearance.bond_ref_no.isnotnull())
		.where(border_clearance.bond_ref_no != '')
		.where(border_clearance.cargo_type == 'Container')
		.where(border_clearance.clearance_type.isin(['Entry', 'Pass Through']))
	)


def get_border_loose_bonds_query():
	border_clearance = frappe.qb.DocType("Border Clearance")
	return (
		frappe.qb.from_(border_clearance)
		.select(
			border_clearance.bond_ref_no.as_("bond_reference"),
			border_clearance.loose_sub_t1_ref.as_("sub_t1"),
			border_clearance.bt_approval_date.as_("bond_date"),
			border_clearance.loose_bond_value.as_("bond_value"),
			border_clearance.cargo_description.as_("cargo"),
			border_clearance.bond_canceled_date.as_("bond_cancellation_date"),
			ConstantColumn('Border Clearance').as_("reference_type"),
			border_clearance.name.as_("reference_doc"),
		)
		.where(border_clearance.bond_ref_no.isnotnull())
		.where(border_clearance.bond_ref_no != '')
		.where(border_clearance.cargo_type == 'Loose Cargo')
		.where(border_clearance.clearance_type.isin(['Entry', 'Pass Through']))
	)
