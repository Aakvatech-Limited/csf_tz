import frappe


def review_permission(doc, ptype=None, user=None):
	"""Tax extensions never grant access to an otherwise inaccessible voucher."""
	if not doc.gl_entry:
		return None
	if frappe.db.exists("GL Entry", doc.gl_entry):
		gl = frappe.get_doc("GL Entry", doc.gl_entry)
		if not frappe.has_permission("GL Entry", "read", doc=gl, user=user):
			return False
		source_type, source_name = gl.voucher_type, gl.voucher_no
	else:
		# A repost can replace GL IDs. Preserve access to the audit record through its voucher.
		source_type, source_name = doc.source_doctype, doc.source_name
	if not source_type or not source_name or not frappe.db.exists(source_type, source_name):
		return False
	source = frappe.get_doc(source_type, source_name)
	if not frappe.has_permission(source.doctype, "read", doc=source, user=user):
		return False
	return None
