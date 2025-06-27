import frappe
from typing import Dict, List
from datetime import datetime, timedelta
from frappe.query_builder import Criterion
from hrms.hr.utils import validate_active_employee
from frappe.utils import cint, get_datetime, now_datetime, add_days
from hrms.hr.doctype.shift_assignment.shift_assignment import (
    get_actual_start_end_datetime_of_shift,
    get_exact_shift,
    get_shift_for_time,
    get_shift_details,
    get_prev_or_next_shift,
)


def validate(doc, method):
    override_fetch_shift_details = frappe.db.get_single_value(
        "CSF TZ Settings", "override_fetch_shift_details"
    )
    if override_fetch_shift_details == 0:
        return
    
    validate_active_employee(doc.employee)
    doc.validate_duplicate_log()
    shift_timings = get_employee_shift_timings(
        doc.employee, get_datetime(doc.time), True
    )
    shift_actual_timings = get_exact_shift(shift_timings, get_datetime(doc.time))
    if shift_actual_timings:
        if (
            shift_actual_timings.shift_type.determine_check_in_and_check_out
            == "Strictly based on Log Type in Employee Checkin"
            and not doc.log_type
            and not doc.skip_auto_attendance
        ):
            frappe.throw(
                _(
                    "Log Type is required for check-ins falling in the shift: {0}."
                ).format(shift_actual_timings.shift_type.name)
            )
        if not doc.attendance:
            doc.shift = shift_actual_timings.shift_type.name
            doc.shift_actual_start = shift_actual_timings.actual_start
            doc.shift_actual_end = shift_actual_timings.actual_end
            doc.shift_start = shift_actual_timings.start_datetime
            doc.shift_end = shift_actual_timings.end_datetime
    else:
        doc.shift = None


def get_employee_shift_timings(
    employee: str, for_timestamp: datetime = None, consider_default_shift: bool = False
) -> List[Dict]:
    """Returns previous shift, current/upcoming shift, next_shift for the given timestamp and employee"""
    if for_timestamp is None:
        for_timestamp = now_datetime()

    # write and verify a test case for midnight shift.
    prev_shift = curr_shift = next_shift = None
    curr_shift = get_employee_shift(
        employee, for_timestamp, consider_default_shift, "forward"
    )
    if curr_shift:
        next_shift = get_employee_shift(
            employee,
            curr_shift.start_datetime + timedelta(days=1),
            consider_default_shift,
            "forward",
        )
    prev_shift = get_employee_shift(
        employee,
        (curr_shift.start_datetime if curr_shift else for_timestamp)
        + timedelta(days=-1),
        consider_default_shift,
        "reverse",
    )

    if curr_shift:
        # adjust actual start and end times if they are overlapping with grace period (before start and after end)
        if prev_shift:
            curr_shift.actual_start = (
                prev_shift.end_datetime
                if curr_shift.actual_start < prev_shift.end_datetime
                else curr_shift.actual_start
            )
            prev_shift.actual_end = (
                curr_shift.actual_start
                if prev_shift.actual_end > curr_shift.actual_start
                else prev_shift.actual_end
            )
        if next_shift:
            next_shift.actual_start = (
                curr_shift.end_datetime
                if next_shift.actual_start < curr_shift.end_datetime
                else next_shift.actual_start
            )
            curr_shift.actual_end = (
                next_shift.actual_start
                if curr_shift.actual_end > next_shift.actual_start
                else curr_shift.actual_end
            )

    return prev_shift, curr_shift, next_shift


def get_employee_shift(
    employee: str,
    for_timestamp: datetime = None,
    consider_default_shift: bool = False,
    next_shift_direction: str = None,
) -> Dict:
    shift_details = {}
    shifts_for_date = get_shifts_for_date(employee, for_timestamp)
    if shifts_for_date:
        shift_details = get_shift_for_time(shifts_for_date, for_timestamp)

    # if shift assignment is not found, consider default shift
    default_shift = frappe.db.get_value(
        "Employee", employee, "default_shift", cache=True
    )
    if not shift_details and consider_default_shift:
        shift_details = get_shift_details(default_shift, for_timestamp)

    # if no shift is found, find next or prev shift assignment based on direction
    if not shift_details and next_shift_direction:
        shift_details = get_prev_or_next_shift(
            employee,
            for_timestamp,
            consider_default_shift,
            default_shift,
            next_shift_direction,
        )

    return shift_details or {}


def get_shifts_for_date(employee: str, for_timestamp: datetime) -> List[Dict[str, str]]:
    """Returns list of shifts with details for given date"""
    for_date = for_timestamp.date()

    assignment = frappe.qb.DocType("Shift Assignment")
    shift_assignments = (
        frappe.qb.from_(assignment)
        .select(
            assignment.name,
            assignment.shift_type,
            assignment.start_date,
            assignment.end_date,
        )
        .where(
            (assignment.employee == employee)
            & (assignment.docstatus == 1)
            & (assignment.status == "Active")
            & (assignment.start_date <= for_date)
            & (
                Criterion.any(
                    [
                        assignment.end_date.isnull(),
                        (
                            assignment.end_date.isnotnull()
                            # for midnight shifts, valid assignments are upto 1 day prior
                            & (for_date <= assignment.end_date)
                        ),
                    ]
                )
            )
        )
    ).run(as_dict=True)
    return shift_assignments
