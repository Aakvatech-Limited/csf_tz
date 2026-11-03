"""Keep the Import File feature in csf_tz while its landed-cost hooks still live here."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	# Reload the original schema under the active module. This keeps the same table,
	# names and records on v15 upgrades and recreates metadata deleted by cleanup.
	frappe.reload_doc("csf_tz", "doctype", "import_file", force=True)
	frappe.clear_cache(doctype="Import File")

	fields = {}
	for doctype, insert_after in (
		("Purchase Invoice", "reference"),
		("Journal Entry", "clearance_date"),
		("Landed Cost Voucher", "sec_break1"),
	):
		meta = frappe.get_meta(doctype)
		# The old section/clearance fields are not present on every installation.
		if not meta.has_field(insert_after):
			insert_after = meta.fields[-1].fieldname if meta.fields else None
		fields[doctype] = [
			{
				"fieldname": "import_file",
				"label": "Import File",
				"fieldtype": "Link",
				"options": "Import File",
				"insert_after": insert_after,
				"allow_on_submit": int(doctype != "Landed Cost Voucher"),
			}
		]

	# Recreate missing links without resetting site-specific settings on existing fields.
	create_custom_fields(fields, update=False)
