# Copyright (c) 2013, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
from frappe.query_builder.functions import Count, Sum
from csf_tz.utils.query_builder import get_expenses_total_query, get_latest_reporting_status_query
import ast
from datetime import datetime

def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "name",
			"label": _("Reference"),
			"fieldtype": "Link",
			"options": "Export",
			"width": 100
		},
		{
			"fieldname": "file_number",
			"label": _("File Number"),
			"fieldtype": "Link",
			"options": "Files",
			"width": 100
		},
		{
			"fieldname": "booking_number",
			"label": _("Booking Number"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "booking_received",
			"label": _("Booking Received"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 100
		},
		{
			"fieldname": "material",
			"label": _("Commodity"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "no_of_containers",
			"label": _("No of Containers"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "weight",
			"label": _("Weight (kg)"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "value",
			"label": _("Cargo Value"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "export_type",
			"label": _("Export Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "eta",
			"label": _("ETA"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "shipper",
			"label": _("Shipper"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "customs_processing_type",
			"label": _("Customs Processing Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "received_repacking_manifest",
			"label": _("Received Repacking Manifest"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "customs_assessment_submission",
			"label": _("Customs Assessment Submission"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "bt_submission_date",
			"label": _("BT Submission Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "bt_approval_date",
			"label": _("BT Approval Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "expenses_usd",
			"label": _("Expenses (USD)"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "expenses_tzs",
			"label": _("Expenses (TZS)"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 200
		}
	]
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))
	
	export = frappe.qb.DocType("Export")
	packing_list = frappe.qb.DocType("Packing List")
	bond_reference = frappe.qb.DocType("Bond Reference Table")
	data = (
		frappe.qb.from_(export)
		.left_join(packing_list).on((packing_list.parenttype == 'Export') & (packing_list.parent == export.name))
		.left_join(bond_reference).on((bond_reference.parenttype == 'Export') & (bond_reference.parent == export.name))
		.select(
			export.name,
			export.client.as_("customer"),
			export.file_number,
			export.booking_number,
			export.booking_received,
			export.export_type,
			export.material,
			Count(packing_list.name).as_("no_of_containers"),
			Sum(packing_list.net_weight).as_("weight"),
			Sum(bond_reference.bond_value).as_("value"),
			export.eta,
			export.shipper,
			export.customs_processing_type,
			export.received_repacking_manifest,
			export.customs_assessment_submission,
			export.bt_submission_date,
			export.bt_approval_date,
			get_expenses_total_query(export.name, "Export", "USD").as_("expenses_usd"),
			get_expenses_total_query(export.name, "Export", "TZS").as_("expenses_tzs"),
			get_latest_reporting_status_query(export.name, "Export").as_("remarks"),
		)
		.where(export.status == filters.status)
		.where(export.booking_received[filters.from_date:filters.to_date])
		.groupby(export.name)
		.run(as_dict=True)
	)
	
	return columns, data
