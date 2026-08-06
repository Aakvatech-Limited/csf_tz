import secrets
import frappe

# ------------ CONFIGURATION ------------
BATCH_SIZE = 1
TIME_BUDGET_SEC = 50
MAX_ATTEMPTS = 2
BASE_BACKOFF = 300
BACKOFF_JITTER = 0.2
SUCCESS_INTERVAL_SECONDS = 60 * 60 * 2
MAX_CALLS_PER_MINUTE = 1
WORKER_ID = frappe.local.site

# ------------ INTERNAL HELPERS ------------
def _now():
    return frappe.utils.now_datetime()

def _jitter(seconds):
    # Generate cryptographically secure random jitter for backoff timing
    # Range: -BACKOFF_JITTER to +BACKOFF_JITTER
    random_factor = (secrets.randbelow(10000) / 10000.0) * 2 - 1  # -1 to 1
    jitter_factor = 1 + (random_factor * BACKOFF_JITTER)
    return int(seconds * jitter_factor)

def get_pending_cycle_delay(doctype):
    try:
        Task = frappe.qb.DocType(doctype)
        pending = (
            frappe.qb.from_(Task)
            .select(Task.name)
            .where(
                (Task.status == "Pending") &
                ((Task.is_deleted.isnull()) | (Task.is_deleted == 0))
            )
        ).run()
        return max(len(pending), 1) * 60
    except Exception:
        return 60

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
                ((Task.is_deleted.isnull()) | (Task.is_deleted == 0))
            )
            .orderby(Task.priority, order=frappe.qb.terms.Order.desc)
            .orderby(Task.name)
            .limit(limit)
        ).run(as_dict=True)

        if not rows:
            rows = (
                frappe.qb.from_(Task)
                .select(Task.name)
                .where(
                    (Task.status == "Failed") &
                    (Task.next_run_at <= now) &
                    ((Task.is_deleted.isnull()) | (Task.is_deleted == 0))
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
            "status": "Pending",
            "attempts": 0,
            "backoff_exp": 0,
            "last_run_at": _now(),
            "claimed_by": "",
            "claimed_at": None,
            "next_run_at": frappe.utils.add_to_date(_now(), seconds=SUCCESS_INTERVAL_SECONDS),
            "last_error": ""
        })
    except Exception as e:
        frappe.log_error(
            title="Queue Mark Done Failed",
            message=f"Error marking task {task.get('name')} as done in {doctype}: {str(e)}"
        )

def mark_failed(doctype, task, err_msg, next_run_at=None, reset_attempts=False):
    try:
        values = {
            "status": "Failed",
            "last_error": err_msg[:1000],
            "last_run_at": _now(),
            "claimed_by": "",
            "claimed_at": None,
            "next_run_at": next_run_at,
        }
        if reset_attempts:
            values.update({
                "attempts": 0,
                "backoff_exp": 0,
            })
        frappe.db.set_value(doctype, task["name"], values)
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
        attempts, _ = bump_attempts(doctype, task)
        cycle_delay = get_pending_cycle_delay(doctype)
        next_delay = max(backoff_seconds, cycle_delay)
        next_run = frappe.utils.add_to_date(_now(), seconds=_jitter(next_delay))
        if attempts >= MAX_ATTEMPTS:
            mark_failed(
                doctype,
                task,
                error_msg or "Max attempts exceeded",
                next_run_at=next_run,
                reset_attempts=True,
            )
            return
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
