import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class TZTaxAccountMapping(Document):
	def validate(self):
		account = frappe.get_doc("Account", self.account)
		account.check_permission("read")
		if account.company != self.company or account.is_group:
			frappe.throw(_("Select a ledger account belonging to the selected company."))
		if self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To cannot precede Valid From."))
		if not self.enabled:
			return
		# Serialise mapping edits for this ledger, including concurrent inserts.
		a = frappe.qb.DocType("Account")
		frappe.qb.from_(a).select(a.name).where(a.name == self.account).for_update().run()
		m = frappe.qb.DocType("TZ Tax Account Mapping")
		overlaps = (
			(
				frappe.qb.from_(m)
				.select(m.name)
				.where((m.company == self.company) & (m.account == self.account) & (m.enabled == 1))
				.where(m.name != (self.name or ""))
				.where(m.valid_from <= (self.valid_to or "9999-12-31"))
				.where(m.valid_to.isnull() | (m.valid_to >= self.valid_from))
			)
			.for_update()
			.run()
		)
		if overlaps:
			frappe.throw(_("Enabled account mappings cannot have overlapping effective periods."))
