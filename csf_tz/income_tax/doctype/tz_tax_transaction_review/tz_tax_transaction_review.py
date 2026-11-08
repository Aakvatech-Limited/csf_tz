from frappe.model.document import Document

from csf_tz.income_tax.service import approve_review, validate_review


class TZTaxTransactionReview(Document):
	def validate(self):
		validate_review(self)

	def before_submit(self):
		approve_review(self)

	def before_cancel(self):
		self.active_gl_entry = None
