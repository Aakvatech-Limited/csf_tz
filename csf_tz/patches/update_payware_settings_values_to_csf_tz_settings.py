import frappe


def execute():
	if not frappe.db.exists("DocType", "Payware Settings"):
		return

	try:
		payware_doc = frappe.get_doc("Payware Settings")
	except frappe.DoesNotExistError:
		return

	csf_tz_doc = frappe.get_doc("CSF TZ Settings")

	for field in [
		"working_hours_per_month",
		"ot_module",
		"default_account_for_additional_component_cash_journal",
	]:
		if not csf_tz_doc.get(field):
			csf_tz_doc.update({field: payware_doc.get(field)})

	csf_tz_doc.save(ignore_permissions=True)
