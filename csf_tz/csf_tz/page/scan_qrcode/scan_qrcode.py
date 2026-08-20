import frappe


@frappe.whitelist()
def add_biometric_log(data):
	"""Add biometric log"""
	log = frappe.new_doc("CSF TZ Biometric Log")
	log.user_id = data
	log.uid = data
	log.timestamp = frappe.utils.now_datetime()
	log.insert(ignore_permissions=True)
	frappe.msgprint("Biometric log added successfully", alert=True)

	return log

	# if not data:
	#     frappe.throw(str(frappe.form_dict))
