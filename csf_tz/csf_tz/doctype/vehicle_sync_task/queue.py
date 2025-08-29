#queue.py
import random
from datetime import datetime
import frappe



# ------------ CONFIGURATION ------------
BATCH_SIZE = 5
TIME_BUDGET_SEC = 50
MAX_ATTEMPTS = 8
BASE_BACKOFF = 300
BACKOFF_JITTER = 0.2
WORKER_ID = frappe.local.site



# ------------ INTERNAL HELPERS ------------
def _now():
    return frappe.utils.now_datetime()



def _jitter(seconds):
    return int(seconds * (1 + random.uniform(-BACKOFF_JITTER, BACKOFF_JITTER)))



# ------------ CORE QUEUE OPERATIONS ------------
def claim_batch(doctype, limit=BATCH_SIZE):
    try:
        now = _now()
        Task = frappe.qb.DocType(doctype)
        
        rows = (
            frappe.qb.from_(Task)
            .select(Task.name)
            .where(
                (Task.status == "Pending") &
                ((Task.next_run_at.isnull()) | (Task.next_run_at <= now)) &
                ((Task.is_deleted.isnull()) | (Task.is_deleted == 0))  # ← IGNORE DELETED TASKS
            )
            .orderby(Task.priority, order=frappe.qb.terms.Order.desc)
            .orderby(Task.name)
            .limit(limit)
        ).run(as_dict=True)


        if not rows:
            return []


        claimed = []
        for row in rows:
            frappe.db.set_value(doctype, row["name"], {
                "status": "Processing",
                "claimed_by": WORKER_ID,
                "claimed_at": now,
                "last_run_at": now,
            })
            data = frappe.db.get_value(doctype, row["name"], ["name", "vehicle_no"], as_dict=True)
            claimed.append(data)
        return claimed
    except Exception as e:
        frappe.log_error(
            title="Queue Claim Batch Failed", 
            message=f"Error claiming batch from {doctype}: {str(e)}"
        )
        return []



def mark_done(doctype, task):
    try:
        frappe.db.set_value(doctype, task["name"], {
            "status": "Done",
            "last_run_at": _now(),
            "claimed_by": "",
            "claimed_at": None,
            "next_run_at": None,
            "last_error": ""
        })
    except Exception as e:
        frappe.log_error(
            title="Queue Mark Done Failed",
            message=f"Error marking task {task.get('name')} as done in {doctype}: {str(e)}"
        )



def mark_failed(doctype, task, err_msg):
    try:
        frappe.db.set_value(doctype, task["name"], {
            "status": "Failed",
            "last_error": err_msg[:1000],
            "last_run_at": _now(),
            "claimed_by": "",
            "claimed_at": None,
            "next_run_at": None,
        })
    except Exception as e:
        frappe.log_error(
            title="Queue Mark Failed Error",
            message=f"Error marking task {task.get('name')} as failed in {doctype}: {str(e)}"
        )



def bump_attempts(doctype, task):
    try:
        current = frappe.db.get_value(
            doctype, task["name"], ["attempts", "backoff_exp"], as_dict=True
        )
        attempts = (current.attempts or 0) + 1
        backoff_exp = min((current.backoff_exp or 0) + 1, 6)
        frappe.db.set_value(doctype, task["name"], {
            "attempts": attempts,
            "backoff_exp": backoff_exp,
            "last_run_at": _now()
        })
        return attempts, backoff_exp
    except Exception as e:
        frappe.log_error(
            title="Queue Bump Attempts Failed",
            message=f"Error bumping attempts for task {task.get('name')} in {doctype}: {str(e)}"
        )
        return 1, 1  # Return default values



def schedule_next(doctype, task, backoff_seconds, error_msg=""):
    try:
        attempts, backoff_exp = bump_attempts(doctype, task)
        if attempts >= MAX_ATTEMPTS:
            mark_failed(doctype, task, error_msg or "Max attempts exceeded")
            return
        next_run = frappe.utils.add_to_date(_now(), seconds=_jitter(backoff_seconds))
        frappe.db.set_value(doctype, task["name"], {
            "status": "Pending",
            "claimed_by": "",
            "claimed_at": None,
            "next_run_at": next_run,
            "last_error": error_msg[:500] if error_msg else "",
        })
    except Exception as e:
        frappe.log_error(
            title="Queue Schedule Next Failed",
            message=f"Error scheduling next run for task {task.get('name')} in {doctype}: {str(e)}"
        )



def reset_stuck_tasks(doctype, timeout_minutes=10):
    try:
        timeout_time = frappe.utils.add_to_date(_now(), minutes=-timeout_minutes)
        Task = frappe.qb.DocType(doctype)
        stuck = (
            frappe.qb.from_(Task)
            .select(Task.name)
            .where(
                (Task.status == "Processing") & 
                (Task.claimed_at < timeout_time) &
                ((Task.is_deleted.isnull()) | (Task.is_deleted == 0))  # ← IGNORE DELETED TASKS
            )
        ).run(as_dict=True)
        
        for row in stuck:
            frappe.db.set_value(doctype, row["name"], {
                "status": "Pending",
                "claimed_by": "",
                "claimed_at": None,
                "next_run_at": _now()
            })
        return len(stuck)
    except Exception as e:
        frappe.log_error(
            title="Queue Reset Stuck Tasks Failed",
            message=f"Error resetting stuck tasks in {doctype}: {str(e)}"
        )
        return 0
