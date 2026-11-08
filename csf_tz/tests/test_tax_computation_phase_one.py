"""Site integration acceptance tests. Run with bench on a migrated ERPNext v16 test site."""

import frappe
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.tests.utils import ERPNextTestSuite
from frappe.utils import nowdate

from csf_tz.csf_tz.report.tz_tax_review_register.tz_tax_review_register import execute
from csf_tz.tax_computation.service import new_review
from csf_tz.tax_computation.setup import setup_phase_one


class TestTaxComputationPhaseOne(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("Journal Entry")
		setup_phase_one()
		self.company = "_Test Company"
		self.expense = frappe.db.get_value(
			"Account",
			{
				"company": self.company,
				"is_group": 0,
				"root_type": "Expense",
				"account_type": ["not in", ["Stock", "Cost of Goods Sold"]],
			},
			"name",
		)
		self.journal = make_journal_entry(
			self.expense, "_Test Cash - _TC", 100, company=self.company, posting_date=nowdate(), submit=True
		)
		self.gl = frappe.db.get_value(
			"GL Entry",
			{
				"voucher_no": self.journal.name,
				"voucher_type": "Journal Entry",
				"account": self.expense,
				"is_cancelled": 0,
			},
			"name",
		)

	def make_review(self, category="Ordinary Business Expense"):
		doc = frappe.get_doc(new_review(self.gl))
		doc.set("allocations", [{"tax_category": category, "amount": 100, "reason": "Test classification"}])
		doc.review_reason = "Test evidence and source checked"
		return doc

	def report_rows(self):
		return execute({"company": self.company, "from_date": nowdate(), "to_date": nowdate()})[1]

	def test_review_does_not_mutate_voucher_and_can_be_amended(self):
		modified = frappe.db.get_value("Journal Entry", self.journal.name, "modified")
		doc = self.make_review().insert()
		doc.submit()
		self.assertEqual(doc.reviewed_by, frappe.session.user)
		self.assertEqual(modified, frappe.db.get_value("Journal Entry", self.journal.name, "modified"))
		self.assertTrue(
			any(row["review"] == doc.name and row["status"] == "Reviewed" for row in self.report_rows())
		)
		doc.cancel()
		self.assertIsNone(frappe.db.get_value(doc.doctype, doc.name, "active_gl_entry"))
		self.make_review().insert()

	def test_tax_review_does_not_block_source_cancellation(self):
		doc = self.make_review().insert()
		doc.submit()
		self.journal.cancel()
		self.assertTrue(
			any(
				row["review"] == doc.name and row["status"] in ("Source Cancelled", "GL Entry Replaced")
				for row in self.report_rows()
			)
		)

	def test_duplicate_review_is_rejected(self):
		self.make_review().insert()
		duplicate = frappe.new_doc("TZ Tax Transaction Review")
		duplicate.gl_entry = self.gl
		duplicate.review_reason = "Duplicate test"
		duplicate.append(
			"allocations", {"tax_category": "Ordinary Business Expense", "amount": 100, "reason": "Test"}
		)
		self.assertRaises(frappe.ValidationError, duplicate.insert)

	def test_partial_allocation_is_rejected(self):
		doc = self.make_review()
		doc.allocations[0].amount = 90
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_missing_evidence_requires_explicit_manager_exception(self):
		doc = self.make_review("Charitable Contribution - Subject to Limit").insert()
		self.assertRaises(frappe.ValidationError, doc.submit)
		doc.reload()
		doc.evidence_exception_reason = "Pending third-party confirmation; manager accepts review exception"
		doc.save()
		doc.submit()
		self.assertTrue(
			any(
				row["review"] == doc.name and row["status"] == "Reviewed with Exception"
				for row in self.report_rows()
			)
		)

	def test_source_change_invalidates_review(self):
		doc = self.make_review().insert()
		doc.submit()
		frappe.db.set_value("Journal Entry", self.journal.name, "user_remark", "Changed after tax approval")
		self.assertTrue(
			any(row["review"] == doc.name and row["status"] == "Source Changed" for row in self.report_rows())
		)

	def test_overlapping_account_mappings_are_rejected(self):
		data = {
			"doctype": "TZ Tax Account Mapping",
			"company": self.company,
			"account": self.expense,
			"tax_category": "Ordinary Business Expense",
			"enabled": 1,
			"valid_from": "2026-01-01",
			"valid_to": "2026-12-31",
		}
		frappe.get_doc(data).insert()
		self.assertRaises(frappe.ValidationError, frappe.get_doc(data).insert)
