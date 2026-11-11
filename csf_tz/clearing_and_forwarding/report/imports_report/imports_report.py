# Copyright (c) 2013, Codes Consult and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
from frappe.query_builder.functions import Concat, Count, Sum
from csf_tz.utils.query_builder import get_expenses_total_query, get_latest_reporting_status_query
import ast
from datetime import datetime
from frappe.desk.reportview import export_query
from frappe.desk.query_report import run
from frappe.desk.query_report import get_columns_dict
from six import string_types
import os, json
import openpyxl
from openpyxl.styles import Font
from openpyxl import load_workbook
from six import StringIO, string_types
from frappe.utils.xlsxutils import handle_html

def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "reference",
			"label": _("Reference"),
			"fieldtype": "Link",
			"options": "Import",
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
			"fieldname": "bl_number",
			"label": _("BL Number"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "cargo",
			"label": _("Cargo"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "number_of_containers",
			"label": _("No. of Containers"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "total_weight",
			"label": _("Total Weight"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "cargo_value",
			"label": _("Cargo Value"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "shipper",
			"label": _("Shipper"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "vessel_name",
			"label": _("Vessel Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "import_type",
			"label": _("Import Type"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "shipping_eta",
			"label": _("Shipping ETA"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "shipping_ata",
			"label": _("Shipping ATA"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "destination",
			"label": _("Destination"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "manifest_date",
			"label": _("Manifest Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "tansad_date",
			"label": _("Tansad Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "manifest_comparison",
			"label": _("Manifest Comparison"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "loading_date",
			"label": _("Loading Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "import_expenses_usd",
			"label": _("Import Expenses"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "import_expenses_tzs",
			"label": _("Import Expenses (TZS)"),
			"fieldtype": "Float",
			"width": 150
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 200
		}
	]
	
	import_doc = frappe.qb.DocType("Import")
	query = get_imports_query(import_doc).where(import_doc.documents_received_date[filters.from_date:filters.to_date])
	
	if filters.status:
		query = query.where(import_doc.status == filters.status)
			
	if filters.loading_date_from:
		query = query.where(import_doc.loading_date >= filters.loading_date_from)
		
	if filters.loading_date_to:
		query = query.where(import_doc.loading_date <= filters.loading_date_to)
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date {}").format(filters.to_date))
	
	data = query.groupby(import_doc.name).run(as_dict=True)
	
	return columns, data

	


def get_imports_query(import_doc):
	cargo = frappe.qb.DocType("Cargo Details")
	return (
		frappe.qb.from_(import_doc)
		.left_join(cargo).on((cargo.parent == import_doc.name) & (cargo.parenttype == 'Import'))
		.select(
			import_doc.name.as_("reference"),
			import_doc.customer,
			import_doc.bl_number,
			Concat(import_doc.cargo, " - ", import_doc.cargo_description).as_("cargo"),
			Count(cargo.name).as_("number_of_containers"),
			Sum(cargo.net_weight).as_("total_weight"),
			Sum(cargo.bond_value).as_("cargo_value"),
			import_doc.shipping_line.as_("shipper"),
			import_doc.vessel_name,
			import_doc.import_type,
			import_doc.eta.as_("shipping_eta"),
			import_doc.ata.as_("shipping_ata"),
			Concat(import_doc.cargo_destination_country, " - ", import_doc.cargo_destination_city).as_("destination"),
			import_doc.manifest_date,
			import_doc.tansad_date,
			import_doc.manifest_comparison_date.as_("manifest_comparison"),
			import_doc.loading_date,
			get_expenses_total_query(import_doc.name, "Import", "USD").as_("import_expenses_usd"),
			get_expenses_total_query(import_doc.name, "Import", "TZS").as_("import_expenses_tzs"),
			get_latest_reporting_status_query(import_doc.name, "Import").as_("remarks"),
		)
	)
