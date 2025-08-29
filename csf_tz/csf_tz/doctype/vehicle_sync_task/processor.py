#processor.py
import json
import requests
from datetime import datetime
from time import sleep
import frappe
import csf_tz.csf_tz.doctype.vehicle_sync_task.queue as queue


# ------------ CONFIGURATION ------------
HOST = "https://tms.tpf.go.tz/api/OffenceCheck"
TASK_DOCTYPE = "Vehicle Sync Task"


# ------------ API INTEGRATION ------------
def _call_external_api(vehicle_no):
    if not vehicle_no or len(vehicle_no) < 7:
        raise Exception(f"Invalid vehicle license plate: {vehicle_no}")

    payload = {"vehicle": vehicle_no}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        sleep(2)
        response = requests.post(HOST, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
    except Exception as e:
        raise Exception(f"API/Parse error for {vehicle_no}: {str(e)}")

    pending_transactions = result.get("pending_transactions", [])
    fine_records_created = 0

    if pending_transactions:
        for tx in pending_transactions:
            ref = tx.get("reference", "")
            if ref and not frappe.db.exists("Vehicle Fine Record", {"vehicle": vehicle_no, "reference": ref}):
                try:
                    rec = frappe.new_doc("Vehicle Fine Record")
                    rec.vehicle = vehicle_no
                    rec.reference = ref
                    rec.amount = tx.get("amount", 0)
                    rec.offense = tx.get("offense", "Traffic Violation")
                    rec.status = "PENDING"
                    rec.fine_date = tx.get("date", frappe.utils.today())
                    rec.insert(ignore_permissions=True)
                    fine_records_created += 1
                except Exception as e:
                    frappe.log_error(
                        title="Vehicle Fine Record Creation Failed",
                        message=f"Error creating fine record for vehicle {vehicle_no}, reference {ref}: {str(e)}"
                    )
    else:
        try:
            existing = frappe.get_all("Vehicle Fine Record",
                filters={"vehicle": vehicle_no, "status": ["!=", "PAID"]},
                pluck="name")
            for record in existing:
                frappe.db.set_value("Vehicle Fine Record", record, "status", "PAID")
        except Exception as e:
            frappe.log_error(
                title="Vehicle Fine Record Update Failed",
                message=f"Error updating fine records to PAID for vehicle {vehicle_no}: {str(e)}"
            )

    return {
        "status": "ok",
        "pending_fines": len(pending_transactions),
        "fine_records_created": fine_records_created,
        "vehicle": vehicle_no
    }


# ------------ MAIN PROCESSOR ------------
@frappe.whitelist()
def run_vehicle_batch():
    start = datetime.utcnow()
    processed, errors = 0, 0

    try:
        queue.reset_stuck_tasks(TASK_DOCTYPE, timeout_minutes=10)
        tasks = queue.claim_batch(TASK_DOCTYPE, limit=5)
        if not tasks:
            return {"status": "no_tasks", "message": f"No pending tasks at {start}"}

        for task in tasks:
            try:
                _call_external_api(task["vehicle_no"])
                queue.mark_done(TASK_DOCTYPE, task)
                processed += 1
            except Exception as e:
                errors += 1
                error_msg = str(e)
                frappe.log_error(
                    title="Vehicle API Processing Failed",
                    message=f"Error processing vehicle {task.get('vehicle_no')}: {error_msg}"
                )
                attempts, backoff_exp = queue.bump_attempts(TASK_DOCTYPE, task)
                if attempts >= queue.MAX_ATTEMPTS:
                    queue.mark_failed(TASK_DOCTYPE, task, error_msg)
                else:
                    backoff_seconds = queue.BASE_BACKOFF * (2 ** backoff_exp)
                    queue.schedule_next(TASK_DOCTYPE, task, backoff_seconds, error_msg)

            if (datetime.utcnow() - start).total_seconds() > queue.TIME_BUDGET_SEC:
                break

        frappe.db.commit()
        total_runtime = (datetime.utcnow() - start).total_seconds()
        return {
            "status": "completed",
            "runtime_seconds": total_runtime,
            "processed": processed,
            "errors": errors,
            "total_claimed": len(tasks)
        }
    except Exception as e:
        frappe.log_error(
            title="Vehicle Batch Processing Failed",
            message=f"Critical error in run_vehicle_batch: {str(e)}"
        )
        return {"status": "error", "message": str(e)}


# ------------ 15-MINUTE CYCLE MANAGEMENT ------------
@frappe.whitelist()
def reset_cycle():
    try:
        Task = frappe.qb.DocType(TASK_DOCTYPE)

        done_tasks = (
            frappe.qb.from_(Task)
            .select(Task.name)
            .where(Task.status == "Done")
        ).run(as_dict=True)

        completed_reset = 0
        for row in done_tasks:
            try:
                frappe.db.set_value(TASK_DOCTYPE, row["name"], {
                    "status": "Pending",
                    "next_run_at": frappe.utils.now(),
                    "claimed_by": "",
                    "claimed_at": None,
                    "last_error": ""
                })
                completed_reset += 1
            except Exception as e:
                frappe.log_error(
                    title="Task Reset Failed",
                    message=f"Error resetting completed task {row['name']}: {str(e)}"
                )

        from frappe.utils import add_to_date, now_datetime
        failed_tasks = (
            frappe.qb.from_(Task)
            .select(Task.name)
            .where((Task.status == "Failed") &
                   (Task.last_run_at < add_to_date(now_datetime(), hours=-1)))
        ).run(as_dict=True)

        failed_reset = 0
        for row in failed_tasks:
            try:
                frappe.db.set_value(TASK_DOCTYPE, row["name"], {
                    "status": "Pending",
                    "next_run_at": frappe.utils.now(),
                    "attempts": 0,
                    "backoff_exp": 0,
                    "claimed_by": "",
                    "claimed_at": None,
                })
                failed_reset += 1
            except Exception as e:
                frappe.log_error(
                    title="Failed Task Reset Error",
                    message=f"Error resetting failed task {row['name']}: {str(e)}"
                )

        frappe.db.commit()
        return {
            "cycle_reset": True,
            "completed_reset": completed_reset,
            "failed_reset": failed_reset,
            "total_reset": completed_reset + failed_reset,
        }
    except Exception as e:
        frappe.log_error(
            title="Cycle Reset Failed",
            message=f"Critical error in reset_cycle: {str(e)}"
        )
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def create_sync_task(vehicle_no, priority=0, immediate=False):
    try:
        # Check for existing active tasks (not deleted)
        existing = frappe.db.get_value(
            TASK_DOCTYPE,
            {
                "vehicle_no": vehicle_no, 
                "status": ["in", ["Pending", "Processing"]],
                "is_deleted": ["!=", 1]  # Only check non-deleted tasks
            },
            "name"
        )
        
        if existing:
            if immediate or priority > 5:
                frappe.db.set_value(TASK_DOCTYPE, existing, {
                    "priority": max(priority, 5),
                    "next_run_at": frappe.utils.now_datetime()
                })
            return existing

        # Check if deleted task exists - reactivate it instead of creating new
        deleted_task = frappe.db.get_value(
            TASK_DOCTYPE,
            {"vehicle_no": vehicle_no, "is_deleted": 1},
            "name"
        )
        
        if deleted_task:
            # Reactivate deleted task
            frappe.db.set_value(TASK_DOCTYPE, deleted_task, {
                "is_deleted": 0,
                "status": "Pending",
                "priority": priority,
                "attempts": 0,
                "backoff_exp": 0,
                "next_run_at": frappe.utils.now_datetime() if immediate else None,
                "claimed_by": "",
                "claimed_at": None,
                "last_error": ""
            })
            return deleted_task

        # Create new task
        task = frappe.new_doc(TASK_DOCTYPE)
        task.vehicle_no = vehicle_no
        task.status = "Pending"
        task.priority = priority
        task.attempts = 0
        task.backoff_exp = 0
        task.is_deleted = 0  # Explicitly set to 0
        task.next_run_at = frappe.utils.now_datetime() if immediate else None
        task.insert(ignore_permissions=True)
        return task.name
        
    except Exception as e:
        frappe.log_error(
            title="Sync Task Creation Failed",
            message=f"Error creating sync task for vehicle {vehicle_no}: {str(e)}"
        )
        return None


@frappe.whitelist()
def seed_vehicle_sync_queue():
    """
    Updated: Handles new vehicles, existing vehicles, and marks deleted ones
    Can be used for initial seeding AND daily sync
    """
    try:
        # Current vehicles from Vehicle doctype
        current_vehicles = frappe.get_all(
            "Vehicle", 
            fields=["license_plate"], 
            filters={"license_plate": ["is", "set"]}
        )
        
        # All existing sync tasks (including deleted ones)
        all_tasks = frappe.get_all(
            TASK_DOCTYPE,
            fields=["vehicle_no", "name", "is_deleted"]
        )
        
        current_plates = {v.license_plate for v in current_vehicles if v.license_plate and len(v.license_plate) >= 7}
        existing_tasks_map = {t.vehicle_no: t for t in all_tasks}
        active_plates = {t.vehicle_no for t in all_tasks if not t.is_deleted}
        
        created = skipped = invalid = reactivated = deleted_marked = 0
        
        # Process current vehicles
        for v in current_vehicles:
            try:
                plate = v.license_plate
                if plate and len(plate) >= 7:
                    if plate not in existing_tasks_map:
                        # New vehicle - create sync task
                        create_sync_task(plate, priority=0)
                        created += 1
                    elif existing_tasks_map[plate].is_deleted:
                        # Previously deleted vehicle is back - reactivate using create_sync_task
                        create_sync_task(plate, priority=0)
                        reactivated += 1
                    else:
                        # Already exists and active
                        skipped += 1
                else:
                    invalid += 1
            except Exception as e:
                frappe.log_error(
                    title="Vehicle Sync Queue Seed Error",
                    message=f"Error processing vehicle {v.get('license_plate', 'Unknown')}: {str(e)}"
                )
        
        # Mark vehicles as deleted if they don't exist in current Vehicle doctype
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
            "total_vehicles": len(current_vehicles),
            "total_valid_plates": len(current_plates)
        }
        
    except Exception as e:
        frappe.log_error(
            title="Seed Vehicle Sync Queue Failed",
            message=f"Critical error in seed_vehicle_sync_queue: {str(e)}"
        )
        return {"status": "error", "message": str(e)}
