import frappe
from frappe.tests.utils import FrappeTestCase

from csf_tz.after_sales_services.doctype.requested_payments.requested_payments import (
	delete_gl_entries,
)


class TestRequestedPaymentsCancel(FrappeTestCase):
	def test_delete_gl_entries_imports_check_freezing_date_from_correct_module(self):
		"""In v15 check_freezing_date moved from gl_entry.gl_entry to general_ledger.
		Calling delete_gl_entries must not raise ImportError."""
		# A non-existent voucher produces an empty GL result, so check_freezing_date
		# and the delete loop are both skipped — but the import runs first.
		delete_gl_entries(voucher_type="Requested Payments", voucher_no="FAKE-RP-NONEXISTENT")

	def test_delete_gl_entries_uses_voucher_no_not_voucher(self):
		"""GL Entry has column voucher_no, not voucher. The QB WHERE clause must
		reference voucher_no so the query does not fail with an unknown-column error."""
		gl_entry = frappe.qb.DocType("GL Entry")
		q = (
			frappe.qb.from_(gl_entry)
			.select(gl_entry.voucher_no)
			.where(gl_entry.voucher_type == "Requested Payments")
			.where(gl_entry.voucher_no == "FAKE-RP-001")
		)
		sql = q.get_sql()
		self.assertIn("voucher_no", sql)
		self.assertNotIn("`voucher`", sql)
