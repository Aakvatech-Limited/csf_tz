from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, get_datetime, now_datetime

from csf_tz.csf_tz.doctype.vehicle_sync_task import processor, queue
from csf_tz.csf_tz.doctype.vehicle_sync_task.vehicle_sync_task import VehicleSyncTask

TASK = "Vehicle Sync Task"


def task_values(name, *fields):
	return frappe.db.get_value(TASK, name, list(fields), as_dict=True)


class TestVehicleSyncQueue(IntegrationTestCase):
	def test_mutating_sync_endpoints_require_post(self):
		for endpoint in (processor.run_vehicle_batch, processor.seed_vehicle_sync_queue):
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[endpoint], ["POST"])

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.commit_patch = patch.object(frappe.db, "commit")
		cls.commit_patch.start()
		cls.addClassCleanup(cls.commit_patch.stop)

	def setUp(self):
		frappe.db.delete(TASK)
		frappe.cache().delete_value(processor.RATE_LIMIT_CACHE_KEY)

	def test_create_sync_task_normalizes_and_deduplicates(self):
		name = processor.create_sync_task("t 100 aaa")
		values = task_values(name, "vehicle_no", "status", "next_run_at", "priority")
		self.assertEqual(values.vehicle_no, "T100AAA")
		self.assertEqual(values.status, "Pending")
		self.assertIsNone(values.next_run_at)

		self.assertEqual(processor.create_sync_task("T100AAA"), name)
		self.assertEqual(task_values(name, "priority").priority, 0)

		self.assertEqual(processor.create_sync_task("T100AAA", immediate=True), name)
		values = task_values(name, "next_run_at", "priority")
		self.assertIsNotNone(values.next_run_at)
		self.assertEqual(values.priority, 5)

		self.assertEqual(processor.create_sync_task("T100AAA", priority=9), name)
		self.assertEqual(task_values(name, "priority").priority, 9)

	def test_create_sync_task_rejects_invalid_plate(self):
		self.assertIsNone(processor.create_sync_task("BAD"))
		self.assertIsNone(processor.create_sync_task(None))

	def test_create_sync_task_reactivates_deleted_task(self):
		name = processor.create_sync_task("T101AAA")
		frappe.db.set_value(TASK, name, {"is_deleted": 1, "status": "Failed", "last_error": "x"})

		self.assertEqual(processor.create_sync_task("T101AAA", priority=2, immediate=True), name)
		values = task_values(name, "is_deleted", "status", "priority", "last_error", "next_run_at")
		self.assertEqual(values.is_deleted, 0)
		self.assertEqual(values.status, "Pending")
		self.assertEqual(values.priority, 2)
		self.assertEqual(values.last_error, "")
		self.assertIsNotNone(values.next_run_at)

	def test_claim_batch_prefers_priority_and_marks_processing(self):
		low = processor.create_sync_task("T102AAA", priority=0)
		high = processor.create_sync_task("T103AAA", priority=3)

		claimed = queue.claim_batch(TASK, limit=1)
		self.assertEqual([row["name"] for row in claimed], [high])
		self.assertEqual(claimed[0]["vehicle_no"], "T103AAA")
		values = task_values(high, "status", "claimed_by", "claimed_at", "last_run_at")
		self.assertEqual(values.status, "Processing")
		self.assertEqual(values.claimed_by, queue.WORKER_ID)
		self.assertIsNotNone(values.claimed_at)
		self.assertIsNotNone(values.last_run_at)

		self.assertEqual([row["name"] for row in queue.claim_batch(TASK, limit=5)], [low])
		self.assertEqual(queue.claim_batch(TASK), [])

	def test_claim_batch_skips_future_and_deleted_tasks(self):
		future = processor.create_sync_task("T104AAA")
		frappe.db.set_value(TASK, future, "next_run_at", add_to_date(now_datetime(), hours=1))
		deleted = processor.create_sync_task("T105AAA")
		frappe.db.set_value(TASK, deleted, "is_deleted", 1)
		self.assertEqual(queue.claim_batch(TASK, limit=5), [])

	def test_claim_batch_falls_back_to_failed_tasks(self):
		name = processor.create_sync_task("T106AAA")
		queue.mark_failed(TASK, {"name": name}, "boom " * 500)
		values = task_values(name, "status", "last_error", "claimed_by", "next_run_at")
		self.assertEqual(values.status, "Failed")
		self.assertEqual(len(values.last_error), 1000)
		self.assertEqual(values.claimed_by, "")
		self.assertIsNotNone(values.next_run_at)

		self.assertEqual([row["name"] for row in queue.claim_batch(TASK)], [name])

	def test_mark_done_schedules_next_run(self):
		name = processor.create_sync_task("T107AAA")
		queue.claim_batch(TASK)
		queue.mark_done(TASK, {"name": name})
		values = task_values(name, "status", "claimed_by", "claimed_at", "next_run_at", "last_error")
		self.assertEqual(values.status, "Pending")
		self.assertEqual(values.claimed_by, "")
		self.assertIsNone(values.claimed_at)
		self.assertEqual(values.last_error, "")
		seconds_ahead = (get_datetime(values.next_run_at) - now_datetime()).total_seconds()
		self.assertGreater(seconds_ahead, queue.SUCCESS_INTERVAL_SECONDS - 120)

	def test_reset_stuck_tasks(self):
		stuck = processor.create_sync_task("T108AAA")
		fresh = processor.create_sync_task("T109AAA")
		frappe.db.set_value(
			TASK, stuck, {"status": "Processing", "claimed_at": add_to_date(now_datetime(), minutes=-30)}
		)
		frappe.db.set_value(TASK, fresh, {"status": "Processing", "claimed_at": now_datetime()})

		self.assertEqual(queue.reset_stuck_tasks(TASK, timeout_minutes=10), 1)
		self.assertEqual(task_values(stuck, "status", "claimed_by").status, "Pending")
		self.assertEqual(task_values(fresh, "status").status, "Processing")

	def test_queue_helpers_log_errors_on_bad_doctype(self):
		with patch("frappe.log_error") as log_error:
			self.assertEqual(queue.claim_batch("No Such DocType"), [])
			queue.mark_done("No Such DocType", {"name": "x"})
			queue.mark_failed("No Such DocType", {"name": "x"}, "err")
			self.assertEqual(queue.reset_stuck_tasks("No Such DocType"), 0)
		self.assertEqual(log_error.call_count, 4)

	def test_rate_limit_slot(self):
		self.assertTrue(processor._acquire_rate_limit_slot())
		for _ in range(queue.MAX_CALLS_PER_MINUTE - 1):
			self.assertTrue(processor._acquire_rate_limit_slot())
		self.assertFalse(processor._acquire_rate_limit_slot())

	def test_run_vehicle_batch_without_tasks(self):
		self.assertEqual(processor.run_vehicle_batch()["status"], "no_tasks")

	def test_run_vehicle_batch_success_and_failure(self):
		name = processor.create_sync_task("T110AAA")
		with patch.object(processor, "sync_vehicle_fines", return_value={"status": "success"}) as sync:
			result = processor.run_vehicle_batch()
		sync.assert_called_once_with("T110AAA")
		self.assertEqual(result, {"status": "completed", "processed": 1, "errors": 0, "claimed": 1})
		self.assertEqual(task_values(name, "status").status, "Pending")

		frappe.db.set_value(TASK, name, "next_run_at", None)
		frappe.cache().delete_value(processor.RATE_LIMIT_CACHE_KEY)
		with patch.object(
			processor, "sync_vehicle_fines", return_value={"status": "retryable_error", "message": "timeout"}
		):
			result = processor.run_vehicle_batch()
		self.assertEqual(result["errors"], 1)
		values = task_values(name, "status", "last_error")
		self.assertEqual(values.status, "Failed")
		self.assertEqual(values.last_error, "timeout")

	def test_run_vehicle_batch_respects_rate_limit(self):
		name = processor.create_sync_task("T111AAA")
		with (
			patch.object(processor, "_acquire_rate_limit_slot", return_value=False),
			patch.object(processor, "sync_vehicle_fines") as sync,
		):
			result = processor.run_vehicle_batch()
		sync.assert_not_called()
		self.assertEqual(result["processed"], 0)
		self.assertIn("limit", task_values(name, "last_error").last_error)

	def test_seed_vehicle_sync_queue(self):
		def records(plates):
			return lambda: iter(frappe._dict(plate_number=plate) for plate in plates)

		with patch.object(
			processor, "get_vehicle_like_records", records(["T120AAA", "t 120 aaa", "T121AAA", "X"])
		):
			result = processor.seed_vehicle_sync_queue()
		self.assertEqual((result["status"], result["created"], result["total_vehicles"]), ("success", 2, 2))

		with patch.object(processor, "get_vehicle_like_records", records(["T120AAA"])):
			result = processor.seed_vehicle_sync_queue()
		self.assertEqual((result["skipped"], result["deleted_marked"]), (1, 1))
		self.assertEqual(frappe.db.get_value(TASK, {"vehicle_no": "T121AAA"}, "is_deleted"), 1)

		with patch.object(processor, "get_vehicle_like_records", records(["T120AAA", "T121AAA"])):
			result = processor.seed_vehicle_sync_queue()
		self.assertEqual((result["skipped"], result["reactivated"]), (1, 1))
		self.assertEqual(frappe.db.get_value(TASK, {"vehicle_no": "T121AAA"}, "is_deleted"), 0)

	def test_seed_vehicle_sync_queue_reports_errors(self):
		with (
			patch.object(processor, "get_vehicle_like_records", side_effect=RuntimeError("meta")),
			patch("frappe.log_error") as log_error,
		):
			result = processor.seed_vehicle_sync_queue()
		self.assertEqual(result, {"status": "error", "message": "meta"})
		log_error.assert_called_once()

	def test_clear_old_logs(self):
		old = processor.create_sync_task("T130AAA")
		recent = processor.create_sync_task("T131AAA")
		frappe.db.set_value(TASK, old, "creation", add_to_date(now_datetime(), days=-10))
		VehicleSyncTask.clear_old_logs(days=7)
		self.assertFalse(frappe.db.exists(TASK, old))
		self.assertTrue(frappe.db.exists(TASK, recent))
