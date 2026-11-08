"""Optional, explicit setup; never overwrite site-maintained classifications."""

import frappe
from frappe import _

CATEGORIES = [
	("Review Required", "Review Required", 0),
	("Ordinary Business Income", "Ordinary Income", 0),
	("Ordinary Business Expense", "Ordinary Expense", 0),
	("Accounting Depreciation", "Add Back", 0),
	("Potential Non-deductible Expense", "Review Required", 0),
	("Charitable Contribution - Subject to Limit", "Restricted Deduction", 1),
	("Statutory Community Contribution", "Restricted Deduction", 1),
	("Potential Exempt Income", "Review Required", 1),
	("Balance Sheet - Review Separately", "Balance Sheet", 0),
]


@frappe.whitelist()
def setup_phase_one():
	if not {"Accounts Manager", "System Manager"}.intersection(frappe.get_roles()):
		frappe.throw(_("Accounts Manager or System Manager is required."), frappe.PermissionError)
	for name, treatment, evidence in CATEGORIES:
		if not frappe.db.exists("TZ Tax Category", name):
			frappe.get_doc(
				{
					"doctype": "TZ Tax Category",
					"category_name": name,
					"treatment": treatment,
					"evidence_required": evidence,
					"guidance": _(
						"Classification only. Confirm eligibility and evidence; annual limits are Phase 2."
					),
				}
			).insert()
	for doctype in ("Purchase Invoice", "Sales Invoice", "Journal Entry", "Payment Entry"):
		if not frappe.db.exists("TZ Tax Source Mapping", doctype):
			frappe.get_doc(
				{
					"doctype": "TZ Tax Source Mapping",
					"reference_doctype": doctype,
					"enabled": 1,
					"company_field": "company",
					"posting_date_field": "posting_date",
				}
			).insert()
	return _("Tax categories and source mappings are ready. Configure account mappings next.")
