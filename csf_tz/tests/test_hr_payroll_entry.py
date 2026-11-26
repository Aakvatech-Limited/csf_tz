from io import BytesIO
from unittest.mock import patch

import frappe
from PyPDF3 import PdfFileWriter

from csf_tz.csftz_hooks import payroll
from csf_tz.tests.hr_payroll_fixtures import (
	HRPayrollTestCase,
	assign_salary_structure,
	get_slips,
	make_department,
	make_payroll_employee,
	make_test_payroll_entry,
	set_csf_tz_settings,
	setup_payroll_master_data,
)


def blank_pdf():
	writer = PdfFileWriter()
	writer.addBlankPage(width=100, height=100)
	buffer = BytesIO()
	writer.write(buffer)
	return buffer.getvalue()


class TestPayrollEntryHooks(HRPayrollTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		setup_payroll_master_data()
		cls.department = make_department("_Test CSF Payroll")
		cls.employee = make_payroll_employee("csf_payroll_entry@example.com", department=cls.department)
		assign_salary_structure(cls.employee, "_Test CSF Payroll Structure")

	def setUp(self):
		super().setUp()
		set_csf_tz_settings(enable_payroll_approval=0)

	def test_payroll_approval_flag_is_set_on_insert(self):
		set_csf_tz_settings(enable_payroll_approval=1)
		payroll_entry = make_test_payroll_entry(self.department)
		self.assertEqual(payroll_entry.has_payroll_approval, 1)

		slips = get_slips(payroll_entry.name)
		self.assertEqual(len(slips), 1)
		self.assertEqual(frappe.db.get_value("Salary Slip", slips[0], "has_payroll_approval"), 1)

	def test_payroll_approval_flag_is_not_set_when_disabled(self):
		payroll_entry = make_test_payroll_entry(self.department)
		self.assertEqual(payroll_entry.has_payroll_approval, 0)
		slip = get_slips(payroll_entry.name)[0]
		self.assertEqual(frappe.db.get_value("Salary Slip", slip, "has_payroll_approval"), 0)

	def test_update_slip_recomputes_draft_slip(self):
		payroll_entry = make_test_payroll_entry(self.department)
		slip = get_slips(payroll_entry.name)[0]
		gross_pay = frappe.db.get_value("Salary Slip", slip, "gross_pay")
		frappe.db.set_value("Salary Slip", slip, "gross_pay", 1)

		self.assertEqual(payroll.update_slip(slip), "updated")
		self.assertEqual(frappe.db.get_value("Salary Slip", slip, "gross_pay"), gross_pay)

	def test_update_slip_skips_submitted_slip(self):
		payroll_entry = make_test_payroll_entry(self.department)
		payroll_entry.submit_salary_slips()
		slip = get_slips(payroll_entry.name, docstatus=1)[0]
		self.assertEqual(payroll.update_slip(slip, show_message=False), "skipped")

	def test_update_slips_enqueues_and_returns_draft_count(self):
		payroll_entry = make_test_payroll_entry(self.department)
		with patch.object(payroll, "enqueue") as enqueue:
			self.assertEqual(payroll.update_slips(payroll_entry.name), 1)
		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["payroll_entry"], payroll_entry.name)

		payroll.enqueue_update_slips(payroll_entry.name)
		self.assertEqual(len(get_slips(payroll_entry.name, docstatus=0)), 1)

	def test_create_journal_entry_requires_submitted_slips(self):
		payroll_entry = make_test_payroll_entry(self.department)
		self.assertRaises(frappe.ValidationError, payroll.create_journal_entry, payroll_entry.name)

	def test_create_journal_entry_for_submitted_slips(self):
		payroll_entry = make_test_payroll_entry(self.department)
		slip = frappe.get_doc("Salary Slip", get_slips(payroll_entry.name)[0])
		slip.submit()

		self.assertEqual(payroll.create_journal_entry(payroll_entry.name), "True")
		journal_entry = frappe.db.get_value("Salary Slip", slip.name, "journal_entry")
		self.assertTrue(journal_entry)
		self.assertEqual(frappe.db.get_value("Journal Entry", journal_entry, "docstatus"), 1)

	def test_create_journal_entry_returns_none_when_already_processed(self):
		payroll_entry = make_test_payroll_entry(self.department)
		payroll_entry.submit_salary_slips()
		payroll_entry.reload()
		self.assertEqual(payroll_entry.salary_slips_submitted, 1)
		self.assertIsNone(payroll.create_journal_entry(payroll_entry.name))

	def test_upload_filed_return_is_private_and_linked_to_processed_payroll(self):
		payroll_entry = make_test_payroll_entry(self.department)
		form = frappe._dict(doctype="Payroll Entry", docname=payroll_entry.name, is_private=0)
		content = blank_pdf()

		with (
			patch.object(frappe.local, "form_dict", form, create=True),
			patch.object(frappe.local, "uploaded_file", content, create=True),
			patch.object(frappe.local, "uploaded_filename", "filed-paye-return.pdf", create=True),
		):
			with self.assertRaises(frappe.ValidationError):
				payroll.upload_filed_return()

			payroll_entry.submit_salary_slips()
			attachment = payroll.upload_filed_return()

		self.assertEqual(attachment.attached_to_doctype, "Payroll Entry")
		self.assertEqual(attachment.attached_to_name, payroll_entry.name)
		self.assertEqual(attachment.is_private, 1)
		self.assertTrue(attachment.file_url.startswith("/private/files/"))
		self.assertEqual(attachment.get_content(), content)

	def test_get_amounts_summary(self):
		payroll_entry = make_test_payroll_entry(self.department)
		frappe.db.set_value("Salary Component", "Basic Salary", "include_in_payroll_summary", 1)
		slip = frappe.get_doc("Salary Slip", get_slips(payroll_entry.name)[0])
		basic = next(row.amount for row in slip.earnings if row.salary_component == "Basic Salary")

		summary = payroll.get_amounts_summary(payroll_entry.name)

		self.assertEqual(summary["gross_pay"], slip.gross_pay)
		self.assertEqual(summary["net_pay"], slip.net_pay)
		self.assertEqual(
			summary["components"], [{"component": "Basic Salary", "label": "Basic Salary", "amount": basic}]
		)

	def test_get_amounts_summary_denies_unprivileged_user(self):
		payroll_entry = make_test_payroll_entry(self.department)
		frappe.set_user("test@example.com")
		try:
			self.assertRaises(frappe.PermissionError, payroll.get_amounts_summary, payroll_entry.name)
		finally:
			frappe.set_user("Administrator")

	def test_print_slips_attaches_pdf(self):
		payroll_entry = make_test_payroll_entry(self.department)
		with patch.object(payroll, "enqueue") as enqueue:
			payroll.print_slips(payroll_entry.name)
		self.assertEqual(enqueue.call_args.kwargs["kwargs"], payroll_entry.name)

		with patch.object(frappe, "get_print", return_value=blank_pdf()):
			attachment = payroll.enqueue_print_slips(payroll_entry.name)

		self.assertEqual(attachment.attached_to_name, payroll_entry.name)
		self.assertEqual(attachment.file_name, payroll_entry.name + ".pdf")

	def test_cancel_with_approval_removes_slips_and_journal_entry(self):
		set_csf_tz_settings(enable_payroll_approval=1)
		payroll_entry = make_test_payroll_entry(self.department)
		payroll_entry.submit_salary_slips()
		slip = get_slips(payroll_entry.name)[0]
		journal_entry = frappe.db.get_value("Salary Slip", slip, "journal_entry")
		self.assertTrue(journal_entry)

		payroll_entry.reload()
		with patch.object(frappe, "log_error") as log_error:
			payroll_entry.cancel()

		log_error.assert_not_called()
		self.assertEqual(get_slips(payroll_entry.name), [])
		self.assertEqual(frappe.db.get_value("Journal Entry", journal_entry, "docstatus"), 2)

	def test_cancel_without_approval_keeps_default_behaviour(self):
		payroll_entry = make_test_payroll_entry(self.department)
		payroll_entry.submit_salary_slips()
		payroll_entry.reload()
		payroll_entry.cancel()
		self.assertEqual(payroll_entry.docstatus, 2)
		self.assertEqual(get_slips(payroll_entry.name), [])


class TestPayrollEntryApprovalWorkflow(HRPayrollTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		setup_payroll_master_data()
		cls.department = make_department("_Test CSF Payroll Approval")
		cls.employee = make_payroll_employee("csf_payroll_approval@example.com", department=cls.department)
		assign_salary_structure(cls.employee, "_Test CSF Payroll Approval Structure")
		set_csf_tz_settings(enable_payroll_approval=1)

	def make_entry(self, workflow_state):
		payroll_entry = make_test_payroll_entry(self.department)
		payroll_entry.workflow_state = workflow_state
		return payroll_entry

	def test_get_workflow_action(self):
		self.assertEqual(
			payroll.get_workflow_action(frappe._dict(workflow_state="Approval Requested")), "Submit"
		)
		self.assertEqual(
			payroll.get_workflow_action(frappe._dict(workflow_state="Change Requested")), "Reject"
		)
		self.assertEqual(payroll.get_workflow_action(frappe._dict(workflow_state="Reviewed by HR")), "Submit")
		self.assertIsNone(payroll.get_workflow_action(frappe._dict(workflow_state="Salary Slips Created")))

	def test_approved_entry_submits_salary_slips(self):
		payroll_entry = self.make_entry("Approved")
		payroll.before_update_after_submit(payroll_entry, None)
		self.assertEqual(len(get_slips(payroll_entry.name, docstatus=1)), 1)

	def test_approval_requested_enqueues_slip_workflow(self):
		payroll_entry = self.make_entry("Approval Requested")
		with patch.object(payroll, "enqueue") as enqueue:
			payroll.before_update_after_submit(payroll_entry, None)
		params = enqueue.call_args.kwargs["kwargs"]
		self.assertEqual(params["action"], "Submit")
		self.assertEqual(params["salary_slips"], get_slips(payroll_entry.name))

	def test_entry_without_approval_does_nothing(self):
		payroll_entry = self.make_entry("Approval Requested")
		payroll_entry.has_payroll_approval = 0
		with patch.object(payroll, "enqueue") as enqueue:
			payroll.before_update_after_submit(payroll_entry, None)
		enqueue.assert_not_called()
