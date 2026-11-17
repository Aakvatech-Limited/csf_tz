# Copyright (c) 2013, Bravo Logisitcs and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
from frappe.query_builder.functions import Count, Sum
from csf_tz.utils.query_builder import get_latest_reporting_status_query
import ast
import datetime

def execute(filters=None):
	columns, data = [], []
	
	columns = [
		{
			"fieldname": "file_number",
			"label": _("File No"),
			"fieldtype": "Link",
			"options": "Export",
			"width": 100
		},
		{
			"fieldname": "client",
			"label": _("Client"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "booking_received",
			"label": _("Booking Received"),
			"fieldtype": "Date",
			"width": 150
		},
		{
			"fieldname": "booking_no",
			"label": _("Booking No"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "commodity",
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
			"label": _("Weight"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "destination",
			"label": _("Destination"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "vessel",
			"label": _("Vessel"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "voyager_no",
			"label": _("Voyager No"),
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "shipping_line",
			"label": _("Shipping Line"),
			"fieldtype": "data",
			"width": 100
		},
		{
			"fieldname": "eta",
			"label": _("ETA"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "engagement_date",
			"label": _("Engagement Date"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "payment_cutoff",
			"label": _("Payment Cutoff"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "stuffing_date",
			"label": _("Stuffing Date"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "tra_release_obtained",
			"label": _("TRA Release Obtained"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "lodge_port_charges",
			"label": _("Lodge Port Charges"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "port_charges_paid",
			"label": _("Port Charges Paid"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "permit_obtained_date",
			"label": _("Permit Obtained Date"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "delivery_date",
			"label": _("Assigned Delivery Date"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "permit_submited_to_client",
			"label": _("Permit Submited to Client"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "containers_arrived_port",
			"label": _("Containers Delivered to Port"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "file_submitted_to_scanner",
			"label": _("File Submitted to Scanner"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "scanner_report_collected",
			"label": _("Scanner Report Collected"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "scanner_report_sent_to_client",
			"label": _("Scanner Report Sent to Client"),
			"fieldtype": "date",
			"width": 100
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "data",
			"width": 150
		}		
	]
	
	today = datetime.date.today().strftime("%Y-%m-%d")
	yesterday =  datetime.date.today() - datetime.timedelta(1)
	day_before = datetime.date.today() - datetime.timedelta(2)
	yesterday = yesterday.strftime("%Y-%m-%d")
	day_before = day_before.strftime("%Y-%m-%d")
	
	export = frappe.qb.DocType("Export")
	query = get_exports_query(export).where(
		export.scanner_report_sent_to_client.isnull()
		| export.scanner_report_sent_to_client.isin([today, yesterday, day_before])
	)
	if filters.customer:
		query = query.where(export.client == filters.customer)
	
	
	data = query.run(as_dict=True)
	
	return columns, data


def get_exports_query(export):
	packing_list = frappe.qb.DocType("Packing List")
	export_packing_list = frappe.qb.from_(packing_list).where(packing_list.parenttype == 'Export').where(packing_list.parent == export.name)
	return (
		frappe.qb.from_(export)
		.select(
			export.name.as_("file_number"),
			export.client,
			export.booking_received,
			export.booking_number.as_("booking_no"),
			export.material.as_("commodity"),
			export_packing_list.select(Count(packing_list.name)).as_("no_of_containers"),
			export_packing_list.select(Sum(packing_list.net_weight)).as_("weight"),
			export.destination,
			export.vessel_name.as_("vessel"),
			export.voyage_no.as_("voyager_no"),
			export.shipping_line,
			export.eta,
			export.engagement_date,
			export.cut_off_date.as_("payment_cutoff"),
			export.stuffing_date,
			export.release_received.as_("tra_release_obtained"),
			export.lodge_port_charges,
			export.port_charges_paid,
			export.loading_permit_received.as_("permit_obtained_date"),
			export.loading_date.as_("delivery_date"),
			export.loading_permit_handover_transporter.as_("permit_submited_to_client"),
			export.containers_arrived_at_port.as_("containers_arrived_port"),
			export.file_submitted_to_scanner,
			export.scanner_report_collected,
			export.scanner_report_sent_to_client,
			get_latest_reporting_status_query(export.name, "Export").as_("remarks"),
		)
		.where(export.status != 'Closed')
	)
