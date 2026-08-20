import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	fields = {
		"CSF TZ Settings": [
			{
				"fieldname": "authority_notification_section",
				"fieldtype": "Section Break",
				"label": "Authority Notifications",
				"insert_after": "tz_regions_populated",
			},
			{
				"fieldname": "enable_latra_license_notifications",
				"fieldtype": "Check",
				"label": "Enable LATRA License Notifications",
				"default": "0",
				"insert_after": "authority_notification_section",
			},
			{
				"fieldname": "enable_latra_offence_notifications",
				"fieldtype": "Check",
				"label": "Enable LATRA Offence Notifications",
				"default": "0",
				"insert_after": "enable_latra_license_notifications",
			},
			{
				"fieldname": "enable_tira_notifications",
				"fieldtype": "Check",
				"label": "Enable TIRA Notifications",
				"default": "0",
				"insert_after": "enable_latra_offence_notifications",
			},
			{
				"fieldname": "enable_vehicle_fine_notifications",
				"fieldtype": "Check",
				"label": "Enable Vehicle Fine Notifications",
				"default": "0",
				"insert_after": "enable_tira_notifications",
			},
			{
				"fieldname": "column_break_authority_notification",
				"fieldtype": "Column Break",
				"insert_after": "enable_vehicle_fine_notifications",
			},
			{
				"fieldname": "latra_license_notify_before_days",
				"fieldtype": "Int",
				"label": "LATRA License Notify Before Days",
				"default": "7",
				"depends_on": "eval:doc.enable_latra_license_notifications",
				"mandatory_depends_on": "eval:doc.enable_latra_license_notifications",
				"insert_after": "column_break_authority_notification",
			},
			{
				"fieldname": "latra_offence_notify_on_new",
				"fieldtype": "Check",
				"label": "LATRA Offence Notify On New",
				"default": "1",
				"depends_on": "eval:doc.enable_latra_offence_notifications",
				"insert_after": "latra_license_notify_before_days",
			},
			{
				"fieldname": "latra_offence_notify_on_status_change",
				"fieldtype": "Check",
				"label": "LATRA Offence Notify On Status Change",
				"default": "0",
				"depends_on": "eval:doc.enable_latra_offence_notifications",
				"insert_after": "latra_offence_notify_on_new",
			},
			{
				"fieldname": "tira_notify_before_days",
				"fieldtype": "Int",
				"label": "TIRA Notify Before Days",
				"default": "7",
				"depends_on": "eval:doc.enable_tira_notifications",
				"mandatory_depends_on": "eval:doc.enable_tira_notifications",
				"insert_after": "latra_offence_notify_on_status_change",
			},
			{
				"fieldname": "vehicle_fine_notify_on_new",
				"fieldtype": "Check",
				"label": "Vehicle Fine Notify On New",
				"default": "1",
				"depends_on": "eval:doc.enable_vehicle_fine_notifications",
				"insert_after": "tira_notify_before_days",
			},
			{
				"fieldname": "vehicle_fine_notify_on_status_change",
				"fieldtype": "Check",
				"label": "Vehicle Fine Notify On Status Change",
				"default": "0",
				"depends_on": "eval:doc.enable_vehicle_fine_notifications",
				"insert_after": "vehicle_fine_notify_on_new",
			},
			{
				"fieldname": "authority_notification_roles",
				"fieldtype": "Table",
				"label": "Authority Notification Roles",
				"options": "Authority Notification Role",
				"insert_after": "vehicle_fine_notify_on_status_change",
			},
		]
	}

	create_custom_fields(fields, update=True)
