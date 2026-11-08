import frappe
from frappe import _
from frappe.model.document import Document


class TZTaxSourceMapping(Document):
	def validate(self):
		meta = frappe.get_meta(self.reference_doctype)
		if meta.istable or meta.issingle or not meta.is_submittable:
			frappe.throw(_("Map a submittable accounting transaction DocType."))
		company = meta.get_field(self.company_field)
		date = meta.get_field(self.posting_date_field)
		if not company or company.fieldtype != "Link" or company.options != "Company":
			frappe.throw(_("Company field must link to Company on the source DocType."))
		if not date or date.fieldtype != "Date":
			frappe.throw(_("Posting date field must be a Date on the source DocType."))
