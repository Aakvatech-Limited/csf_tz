import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from csf_tz.csf_tz.doctype.vehicle_sync_task import queue

TASK_DOCTYPE = "Vehicle Sync Task"


class TestVehicleSyncQueue(FrappeTestCase):
	def create_task(self, **kwargs):
		values = {
			"doctype": TASK_DOCTYPE,
			"vehicle_no": f"TEST-{frappe.generate_hash(length=10)}",
			"status": "Pending",
			"priority": 999999,
			"attempts": 0,
			"backoff_exp": 0,
			"is_deleted": 0,
			"next_run_at": now_datetime(),
		}
		values.update(kwargs)
		return frappe.get_doc(values).insert(ignore_permissions=True)

	def test_claim_batch_records_worker_id(self):
		task = self.create_task()

		claimed = queue.claim_batch(TASK_DOCTYPE, limit=1)

		self.assertEqual(len(claimed), 1)
		self.assertEqual(claimed[0].name, task.name)

		status, claimed_by, claimed_at = frappe.db.get_value(
			TASK_DOCTYPE,
			task.name,
			["status", "claimed_by", "claimed_at"],
		)

		self.assertEqual(status, "Processing")
		self.assertEqual(claimed_by, queue.WORKER_ID)
		self.assertIsNotNone(claimed_at)

	def test_mark_done_clears_worker_identity(self):
		task = self.create_task()

		claimed = queue.claim_batch(TASK_DOCTYPE, limit=1)
		self.assertEqual(len(claimed), 1)

		queue.mark_done(TASK_DOCTYPE, claimed[0])

		status, claimed_by, claimed_at = frappe.db.get_value(
			TASK_DOCTYPE,
			task.name,
			["status", "claimed_by", "claimed_at"],
		)

		self.assertEqual(status, "Pending")
		self.assertFalse(claimed_by)
		self.assertIsNone(claimed_at)

	def test_mark_failed_clears_worker_identity(self):
		task = self.create_task()

		claimed = queue.claim_batch(TASK_DOCTYPE, limit=1)
		self.assertEqual(len(claimed), 1)

		queue.mark_failed(TASK_DOCTYPE, claimed[0], "Test failure")

		status, claimed_by, claimed_at, last_error = frappe.db.get_value(
			TASK_DOCTYPE,
			task.name,
			["status", "claimed_by", "claimed_at", "last_error"],
		)

		self.assertEqual(status, "Failed")
		self.assertFalse(claimed_by)
		self.assertIsNone(claimed_at)
		self.assertEqual(last_error, "Test failure")

	def test_reset_stuck_task_clears_worker_identity(self):
		task = self.create_task(
			status="Processing",
			claimed_by=queue.WORKER_ID,
			claimed_at=add_to_date(now_datetime(), minutes=-20),
		)

		queue.reset_stuck_tasks(TASK_DOCTYPE, timeout_minutes=10)

		status, claimed_by, claimed_at = frappe.db.get_value(
			TASK_DOCTYPE,
			task.name,
			["status", "claimed_by", "claimed_at"],
		)

		self.assertEqual(status, "Pending")
		self.assertFalse(claimed_by)
		self.assertIsNone(claimed_at)
