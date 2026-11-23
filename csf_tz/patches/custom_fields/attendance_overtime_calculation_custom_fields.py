from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	fields = {
		"Employee": [
			{
				"fieldname": "overtime_applicable",
				"label": "Overtime Applicable",
				"fieldtype": "Check",
				"insert_after": "holiday_list",
			},
			{
				"fieldname": "on_approval_overtime",
				"label": "On Approval Overtime",
				"fieldtype": "Check",
				"insert_after": "overtime_applicable",
				"depends_on": "eval:doc.overtime_applicable== 1",
			},
		],
		"Attendance": [
			{
				"fieldname": "start_time",
				"label": "Start Time",
				"fieldtype": "Time",
				"insert_after": "column_break_18",
				"fetch_from": "shift.start_time",
				"read_only": 1,
				"translatable": 1,
			},
			{
				"fieldname": "end_time",
				"label": "End Time",
				"fieldtype": "Time",
				"insert_after": "start_time",
				"fetch_from": "shift.end_time",
				"read_only": 1,
				"translatable": 1,
			},
			{
				"fieldname": "overtime",
				"label": "Overtime",
				"fieldtype": "Section Break",
				"insert_after": "early_exit",
				"collapsible": 1,
			},
			{
				"fieldname": "eligible_working_hours",
				"label": "Eligible Working Hours",
				"fieldtype": "Time",
				"insert_after": "overtime",
				"read_only": 1,
			},
			{
				"fieldname": "eligible_overtime_normal",
				"label": "Eligible Overtime Normal",
				"fieldtype": "Time",
				"insert_after": "eligible_working_hours",
				"read_only": 1,
			},
			{
				"fieldname": "eligible_overtime_holiday",
				"label": "Eligible Overtime Holiday",
				"fieldtype": "Time",
				"insert_after": "eligible_overtime_normal",
				"read_only": 1,
			},
			{
				"fieldname": "column_break_overtime_applicable",
				"fieldtype": "Column Break",
				"insert_after": "eligible_overtime_holiday",
			},
			{
				"fieldname": "overtime_applicable",
				"label": "Overtime Applicable",
				"fieldtype": "Check",
				"insert_after": "column_break_overtime_applicable",
				"fetch_from": "employee.overtime_applicable",
			},
			{
				"fieldname": "on_approval_overtime",
				"label": "On Approval Overtime",
				"fieldtype": "Check",
				"insert_after": "overtime_applicable",
				"fetch_from": "employee.on_approval_overtime",
			},
			{
				"fieldname": "excess_overtime_normal",
				"label": "Excess Overtime Normal",
				"fieldtype": "Time",
				"insert_after": "on_approval_overtime",
				"read_only": 1,
			},
			{
				"fieldname": "excess_overtime_holiday",
				"label": "Excess Overtime Holiday",
				"fieldtype": "Time",
				"insert_after": "excess_overtime_normal",
				"read_only": 1,
			},
		],
		"Shift Type": [
			{
				"fieldname": "overtime_threshold",
				"label": "Overtime Threshold",
				"fieldtype": "Section Break",
				"insert_after": "early_exit_grace_period",
				"collapsible": 1,
			},
			{
				"fieldname": "monday_threshold",
				"label": "Monday Threshold",
				"fieldtype": "Time",
				"insert_after": "overtime_threshold",
			},
			{
				"fieldname": "tuesday_threshold",
				"label": "Tuesday Threshold",
				"fieldtype": "Time",
				"insert_after": "monday_threshold",
			},
			{
				"fieldname": "wednesday_threshold",
				"label": "Wednesday Threshold",
				"fieldtype": "Time",
				"insert_after": "tuesday_threshold",
			},
			{
				"fieldname": "thursday_threshold",
				"label": "Thursday Threshold",
				"fieldtype": "Time",
				"insert_after": "wednesday_threshold",
			},
			{
				"fieldname": "friday_threshold",
				"label": "Friday Threshold",
				"fieldtype": "Time",
				"insert_after": "thursday_threshold",
			},
			{
				"fieldname": "saturday_threshold",
				"label": "Saturday Threshold",
				"fieldtype": "Time",
				"insert_after": "friday_threshold",
			},
			{
				"fieldname": "sunday_threshold",
				"label": "Sunday Threshold",
				"fieldtype": "Time",
				"insert_after": "saturday_threshold",
			},
			{
				"fieldname": "column_break_overtime_holiday",
				"fieldtype": "Column Break",
				"insert_after": "sunday_threshold",
			},
			{
				"fieldname": "overtime_holiday",
				"label": "Overtime Holiday",
				"fieldtype": "Link",
				"insert_after": "column_break_overtime_holiday",
				"options": "Holiday List",
			},
		],
	}

	create_custom_fields(fields, update=True)
