from datetime import datetime, timedelta

import frappe
from frappe.utils import (
	get_datetime,
	get_time,
	get_weekday,
	time_diff,
)


def process_overtime(doc, method):
	if not frappe.db.get_single_value("CSF TZ Settings", "enable_overtime_calculation"):
		return

	if doc.status != "Present" or not doc.overtime_applicable or not doc.in_time or not doc.out_time:
		doc.eligible_working_hours = "00:00:00"
		doc.eligible_overtime_normal = "00:00:00"
		doc.eligible_overtime_holiday = "00:00:00"
		doc.excess_overtime_normal = "00:00:00"
		doc.excess_overtime_holiday = "00:00:00"

		return

	shift_type = frappe.get_doc("Shift Type", doc.shift)
	if not shift_type.overtime_holiday:
		frappe.throw(f"Please set overtime holiday in shift type {shift_type.name}")

	late_entry_grace_period = None
	early_exit_grace_period = None
	if shift_type.enable_entry_grace_period == 1 and shift_type.late_entry_grace_period is not None:
		late_entry_grace_period = shift_type.late_entry_grace_period

	if shift_type.enable_exit_grace_period == 1 and shift_type.early_exit_grace_period is not None:
		early_exit_grace_period = shift_type.early_exit_grace_period

	in_time = doc.in_time or "00:00:00"
	out_time = doc.out_time or "00:00:00"
	checkin_time = get_time(str(in_time))
	checkout_time = get_time(str(out_time))
	start_time = doc.start_time or "00:00:00"
	end_time = doc.end_time or "00:00:00"

	shift_start_time, excess_in_time = calculate_shift_start_time(
		checkin_time, start_time, late_entry_grace_period
	)
	shift_end_time, excess_out_time = calculate_shift_end_time(
		checkout_time, end_time, early_exit_grace_period
	)

	eligible_working_hours = None
	if get_time(str(shift_end_time)) > get_time(str(shift_start_time)):
		eligible_working_hours = time_diff(str(shift_end_time), str(shift_start_time))
	else:
		eligible_working_hours = time_diff(str(shift_start_time), str(shift_end_time))

	threshold = get_weekday_threshold(shift_type, doc.attendance_date)

	is_holiday = get_holiday_status(shift_type.overtime_holiday, doc.attendance_date)

	set_eligible_and_excess_overtime(
		doc,
		excess_in_time,
		excess_out_time,
		eligible_working_hours,
		threshold,
		is_holiday,
	)


def calculate_shift_start_time(checkin_time, start_time, late_entry_grace_period):
	_shift_start_time = None
	_excess_in_time = None
	if checkin_time < get_time(str(start_time)):
		_shift_start_time = get_time(str(start_time))
		_excess_in_time = time_diff(str(start_time), str(checkin_time))
	else:
		if late_entry_grace_period is not None:
			late_entry_time = timedelta(minutes=late_entry_grace_period)
			start_time_ = datetime.strptime(str(start_time), "%H:%M:%S")
			late_entry_datetime = start_time_ + late_entry_time

			if checkin_time <= get_time(late_entry_datetime):
				_shift_start_time = get_time(str(start_time))
			else:
				_shift_start_time = checkin_time
		else:
			_shift_start_time = checkin_time

	if _excess_in_time:
		excess_in_time = _excess_in_time
	else:
		excess_in_time = "00:00:00"

	if _shift_start_time:
		shift_start_time = _shift_start_time
	else:
		shift_start_time = "00:00:00"
	return shift_start_time, excess_in_time


def calculate_shift_end_time(checkout_time, end_time, early_exit_grace_period):
	_shift_end_time = None
	_excess_out_time = None
	if checkout_time > get_time(str(end_time)):
		_shift_end_time = get_time(str(end_time))
		_excess_out_time = time_diff(str(checkout_time), str(end_time))
	else:
		if early_exit_grace_period is not None:
			early_exit_time = timedelta(minutes=early_exit_grace_period)
			end_time_ = datetime.strptime(str(end_time), "%H:%M:%S")
			early_exit_datetime = end_time_ - early_exit_time

			if checkout_time >= get_time(early_exit_datetime):
				_shift_end_time = get_time(str(end_time))
			else:
				_shift_end_time = checkout_time
		else:
			_shift_end_time = checkout_time

	if _excess_out_time:
		excess_out_time = _excess_out_time
	else:
		excess_out_time = "00:00:00"

	if _shift_end_time:
		shift_end_time = _shift_end_time
	else:
		pass
	return shift_end_time, excess_out_time


def get_weekday_threshold(shift_type, attendance_date):
	day = get_weekday(get_datetime(attendance_date))
	threshold = None
	if day == "Monday":
		threshold = shift_type.monday_threshold

	if day == "Tuesday":
		threshold = shift_type.tuesday_threshold

	if day == "Wednesday":
		threshold = shift_type.wednesday_threshold

	if day == "Thursday":
		threshold = shift_type.thursday_threshold

	if day == "Friday":
		threshold = shift_type.friday_threshold

	if day == "Saturday":
		threshold = shift_type.saturday_threshold

	if day == "Sunday":
		threshold = shift_type.sunday_threshold

	return threshold


def get_holiday_status(overtime_holiday, attendance_date):
	if frappe.db.exists(
		"Holiday",
		{
			"parent": overtime_holiday,
			"parentfield": "holidays",
			"holiday_date": attendance_date,
		},
	):
		return True

	return False


def set_eligible_and_excess_overtime(
	doc, excess_in_time, excess_out_time, eligible_working_hours, threshold, is_holiday
):
	eligible_overtime_normal = None
	excess_overtime_normal = None
	eligible_overtime_holiday = None
	excess_overtime_holiday = None

	excess_in_ = get_time(str(excess_in_time))
	excess_out_ = get_time(str(excess_out_time))
	excess_in_timedelta = timedelta(
		hours=excess_in_.hour, minutes=excess_in_.minute, seconds=excess_in_.second
	)
	excess_out_timedelta = timedelta(
		hours=excess_out_.hour, minutes=excess_out_.minute, seconds=excess_out_.second
	)

	if not is_holiday:
		if eligible_working_hours > threshold:
			eligible_overtime_normal = time_diff(str(eligible_working_hours), str(threshold))

		excess_overtime_normal = excess_in_timedelta + excess_out_timedelta
	else:
		eligible_overtime_holiday = eligible_working_hours
		excess_overtime_holiday = excess_in_timedelta + excess_out_timedelta

	doc.eligible_working_hours = eligible_working_hours or "00:00:00"

	if doc.on_approval_overtime == 1:
		if eligible_overtime_normal:
			overtime_normal = datetime.strptime(str(eligible_overtime_normal), "%H:%M:%S")
		else:
			overtime_normal = datetime.strptime(str("00:00:00"), "%H:%M:%S")
		if excess_overtime_normal:
			excess_normal = datetime.strptime(str(excess_overtime_normal), "%H:%M:%S")
		else:
			excess_normal = datetime.strptime(str("00:00:00"), "%H:%M:%S")

		excess_overtime = overtime_normal + timedelta(
			hours=excess_normal.hour,
			minutes=excess_normal.minute,
			seconds=excess_normal.second,
		)
		doc.eligible_overtime_normal = "00:00:00"
		doc.excess_overtime_normal = excess_overtime or "00:00:00"

		if eligible_overtime_holiday:
			overtime_holiday = datetime.strptime(str(eligible_overtime_holiday), "%H:%M:%S")
		else:
			overtime_holiday = datetime.strptime(str("00:00:00"), "%H:%M:%S")
		if excess_overtime_holiday:
			excess_holiday = datetime.strptime(str(excess_overtime_holiday), "%H:%M:%S")
		else:
			excess_holiday = datetime.strptime(str("00:00:00"), "%H:%M:%S")

		excess_overtime_holiday = overtime_holiday + timedelta(
			hours=excess_holiday.hour,
			minutes=excess_holiday.minute,
			seconds=excess_holiday.second,
		)
		doc.eligible_overtime_holiday = "00:00:00"
		doc.excess_overtime_holiday = excess_overtime_holiday or "00:00:00"

	else:
		eligible_overtime_normal___ = (
			"00:00:00" if "day" in str(eligible_overtime_normal) else eligible_overtime_normal
		)
		eligible_overtime_holiday___ = (
			"00:00:00" if "day" in str(eligible_overtime_holiday) else eligible_overtime_holiday
		)
		doc.eligible_overtime_normal = eligible_overtime_normal___ or "00:00:00"
		doc.eligible_overtime_holiday = eligible_overtime_holiday___ or "00:00:00"
		doc.excess_overtime_normal = excess_overtime_normal or "00:00:00"
		doc.excess_overtime_holiday = excess_overtime_holiday or "00:00:00"
