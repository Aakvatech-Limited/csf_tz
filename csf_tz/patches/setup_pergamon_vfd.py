"""Idempotent Pergamon provider setup during install and migrate."""

import frappe


def execute():
	"""Register the provider; company-specific credentials are entered separately."""
	if not frappe.db.exists("DocType", "Pergamon VFD Settings"):
		return
	if frappe.db.exists("VFD Provider", {"vfd_provider_settings": "Pergamon VFD Settings"}):
		return
	frappe.get_doc(
		{
			"doctype": "VFD Provider",
			"vfd_provider": "Pergamon",
			"vfd_provider_settings": "Pergamon VFD Settings",
			"sandbox": 0,
		}
	).insert(ignore_permissions=True)
