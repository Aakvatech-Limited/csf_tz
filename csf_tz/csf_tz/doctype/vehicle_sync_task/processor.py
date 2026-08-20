import json
import time

import frappe

from csf_tz.csf_tz.doctype.vehicle_fine_record.vehicle_fine_record import (
	is_valid_number_plate,
	normalize_number_plate,
	sync_vehicle_fines,
)
from csf_tz.csf_tz.doctype.vehicle_sync_task import queue
from csf_tz.vehicle_authority import get_vehicle_like_records

TASK_DOCTYPE = "Vehicle Sync Task"
RATE_LIMIT_CACHE_KEY = "vehicle_sync_task:tpf_calls"


def _get_current_plates():
	plates = {}
	for record in get_vehicle_like_records():
		plate = normalize_number_plate(record.plate_number)
		if not plate or not is_valid_number_plate(plate):
			continue
		plates[plate] = plate
	return sorted(plates)


def _acquire_rate_limit_slot():
	now_ts = time.time()
	cache = frappe.cache()
	raw = cache.get_value(RATE_LIMIT_CACHE_KEY)

	try:
		timestamps = json.loads(raw) if raw else []
	except Exception:
		timestamps = []

	timestamps = [ts for ts in timestamps if now_ts - float(ts) < 60]
	if len(timestamps) >= queue.MAX_CALLS_PER_MINUTE:
		cache.set_value(RATE_LIMIT_CACHE_KEY, json.dumps(timestamps), expires_in_sec=60)
		return False

	timestamps.append(now_ts)
	cache.set_value(RATE_LIMIT_CACHE_KEY, json.dumps(timestamps), expires_in_sec=60)
	return True


def _backoff_seconds(attempts):
	exponent = max(attempts - 1, 0)
	return queue.BASE_BACKOFF * (2**exponent)


@frappe.whitelist()
def run_vehicle_batch():
	started_at = time.monotonic()
	processed = 0
	errors = 0

	queue.reset_stuck_tasks(TASK_DOCTYPE, timeout_minutes=10)
	tasks = queue.claim_batch(TASK_DOCTYPE, limit=queue.BATCH_SIZE)

	if not tasks:
		return {"status": "no_tasks", "message": "No pending vehicle sync tasks"}

	for task in tasks:
		if (time.monotonic() - started_at) >= queue.TIME_BUDGET_SEC:
			break

		if not _acquire_rate_limit_slot():
			queue.schedule_next(
				TASK_DOCTYPE,
				task,
				60,
				"TPF per-minute limit reached for this site",
			)
			continue

		result = sync_vehicle_fines(task["vehicle_no"])
		status = result.get("status")

		if status == "success":
			queue.mark_done(TASK_DOCTYPE, task)
			processed += 1
			continue

		if status in {"rate_limited", "retryable_error"}:
			attempts, _ = queue.bump_attempts(TASK_DOCTYPE, task)
			queue.schedule_next(
				TASK_DOCTYPE,
				task,
				_backoff_seconds(attempts),
				result.get("message") or status,
			)
			errors += 1
			continue

		queue.mark_failed(
			TASK_DOCTYPE,
			task,
			result.get("message") or "Unhandled sync error",
		)
		errors += 1

	frappe.db.commit()
	return {
		"status": "completed",
		"processed": processed,
		"errors": errors,
		"claimed": len(tasks),
	}


@frappe.whitelist()
def create_sync_task(vehicle_no, priority=0, immediate=False):
	try:
		vehicle_no = normalize_number_plate(vehicle_no)
		if not vehicle_no or not is_valid_number_plate(vehicle_no):
			return None

		existing = frappe.db.get_value(
			TASK_DOCTYPE,
			{
				"vehicle_no": vehicle_no,
				"status": ["in", ["Pending", "Processing"]],
				"is_deleted": ["!=", 1],
			},
			"name",
		)

		if existing:
			if immediate or priority > 5:
				frappe.db.set_value(
					TASK_DOCTYPE,
					existing,
					{
						"priority": max(priority, 5),
						"next_run_at": frappe.utils.now_datetime(),
					},
				)
			return existing

		deleted_task = frappe.db.get_value(
			TASK_DOCTYPE,
			{"vehicle_no": vehicle_no, "is_deleted": 1},
			"name",
		)

		if deleted_task:
			frappe.db.set_value(
				TASK_DOCTYPE,
				deleted_task,
				{
					"is_deleted": 0,
					"status": "Pending",
					"priority": priority,
					"attempts": 0,
					"backoff_exp": 0,
					"next_run_at": frappe.utils.now_datetime() if immediate else None,
					"claimed_by": "",
					"claimed_at": None,
					"last_error": "",
				},
			)
			return deleted_task

		task = frappe.new_doc(TASK_DOCTYPE)
		task.vehicle_no = vehicle_no
		task.status = "Pending"
		task.priority = priority
		task.attempts = 0
		task.backoff_exp = 0
		task.is_deleted = 0
		task.next_run_at = frappe.utils.now_datetime() if immediate else None
		task.insert(ignore_permissions=True)
		return task.name

	except Exception as exc:
		frappe.log_error(
			title="Sync Task Creation Failed",
			message=f"Error creating sync task for vehicle {vehicle_no}: {str(exc)}",
		)
		return None


@frappe.whitelist()
def seed_vehicle_sync_queue():
	try:
		current_plates = set(_get_current_plates())
		all_tasks = frappe.get_all(
			TASK_DOCTYPE,
			fields=["vehicle_no", "name", "is_deleted"],
		)
		existing_tasks_map = {task.vehicle_no: task for task in all_tasks}
		active_plates = {task.vehicle_no for task in all_tasks if not task.is_deleted}

		created = skipped = invalid = reactivated = deleted_marked = 0

		for number_plate in current_plates:
			if number_plate not in existing_tasks_map:
				create_sync_task(number_plate, priority=0)
				created += 1
			elif existing_tasks_map[number_plate].is_deleted:
				create_sync_task(number_plate, priority=0)
				reactivated += 1
			else:
				skipped += 1

		for plate in active_plates:
			if plate not in current_plates:
				task_name = existing_tasks_map[plate].name
				frappe.db.set_value(TASK_DOCTYPE, task_name, "is_deleted", 1)
				deleted_marked += 1

		frappe.db.commit()
		return {
			"status": "success",
			"created": created,
			"skipped": skipped,
			"invalid": invalid,
			"reactivated": reactivated,
			"deleted_marked": deleted_marked,
			"total_vehicles": len(current_plates),
			"total_valid_plates": len(current_plates),
		}
	except Exception as exc:
		frappe.log_error(
			title="Seed Vehicle Sync Queue Failed",
			message=f"Critical error in seed_vehicle_sync_queue: {str(exc)}",
		)
		return {"status": "error", "message": str(exc)}
