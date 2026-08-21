import frappe

BATCH_SIZE = 1
SUCCESS_INTERVAL_SECONDS = 60 * 60 * 24
MAX_CALLS_PER_MINUTE = 1
WORKER_ID = frappe.local.site

def _now():
    return frappe.utils.now_datetime()

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

def mark_failed(doctype, task, err_msg):
    try:
        values = {
            "status": "Failed",
            "attempts": 0,
            "backoff_exp": 0,
            "last_error": err_msg[:1000],
            "last_run_at": _now(),
            "claimed_by": "",
            "claimed_at": None,
            "next_run_at": _now(),
        }
        frappe.db.set_value(doctype, task["name"], values)
    except Exception as e:
        frappe.log_error(
            title="Queue Mark Failed Error",
            message=f"Error marking task {task.get('name')} as failed in {doctype}: {str(e)}"
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
