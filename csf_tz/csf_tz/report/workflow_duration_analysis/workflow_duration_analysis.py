# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

# Copyright (c) 2025, CSF TZ and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, time_diff_in_hours

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    return columns, data, None, chart

def get_columns():
    return [
        {"fieldname": "workflow", "label": _("Workflow"), "fieldtype": "Link", "options": "Workflow", "width": 150},
        {"fieldname": "state", "label": _("State"), "fieldtype": "Data", "width": 120},
        {"fieldname": "avg_duration_hours", "label": _("Avg Duration (Hours)"), "fieldtype": "Float", "width": 130},
        {"fieldname": "min_duration_hours", "label": _("Min Duration (Hours)"), "fieldtype": "Float", "width": 130},
        {"fieldname": "max_duration_hours", "label": _("Max Duration (Hours)"), "fieldtype": "Float", "width": 130},
        {"fieldname": "total_transitions", "label": _("Total Transitions"), "fieldtype": "Int", "width": 120},
        {"fieldname": "avg_duration_formatted", "label": _("Avg Duration (Formatted)"), "fieldtype": "Data", "width": 150}
    ]

def get_data(filters):
    conditions = get_conditions(filters)

    transition_data = frappe.db.sql(f"""
        SELECT 
            wth1.workflow,
            wth1.current_state as state,
            wth1.reference_name,
            wth1.transition_date,
            (SELECT MIN(wth2.transition_date) 
             FROM `tabWorkflow Transition History` wth2 
             WHERE wth2.reference_name = wth1.reference_name 
             AND wth2.transition_date > wth1.transition_date) as next_transition_date
        FROM `tabWorkflow Transition History` wth1
        {conditions}
        ORDER BY wth1.workflow, wth1.current_state, wth1.transition_date
    """, filters, as_dict=1)

    state_durations = {}

    for record in transition_data:
        if record.next_transition_date:
            duration_hours = time_diff_in_hours(record.next_transition_date, record.transition_date)
            key = (record.workflow, record.state)
            state_durations.setdefault(key, []).append(duration_hours)

    result = []
    for (workflow, state), durations in state_durations.items():
        if durations:
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            result.append({
                'workflow': workflow,
                'state': state,
                'avg_duration_hours': flt(avg_duration, 2),
                'min_duration_hours': flt(min_duration, 2),
                'max_duration_hours': flt(max_duration, 2),
                'total_transitions': len(durations),
                'avg_duration_formatted': format_duration(avg_duration)
            })

    return sorted(result, key=lambda x: (x['workflow'], x['avg_duration_hours']))

def format_duration(hours):
    if hours < 1:
        return f"{int(hours * 60)} minutes"
    elif hours < 24:
        return f"{flt(hours, 1)} hours"
    else:
        days = int(hours / 24)
        remaining_hours = int(hours % 24)
        return f"{days} days, {remaining_hours} hours"

def get_chart_data(data):
    if not data:
        return None

    top_states = data[:10]
    labels = [f"{d['workflow']} → {d['state']}" for d in top_states]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Avg Duration",
                    "values": [d['avg_duration_hours'] for d in top_states]
                },
                {
                    "name": "Min Duration",
                    "values": [d['min_duration_hours'] for d in top_states]
                },
                {
                    "name": "Max Duration",
                    "values": [d['max_duration_hours'] for d in top_states]
                }
            ]
        },
        "type": "bar",
        "colors": ["#4caf50", "#2196f3", "#f44336"],
        "title": "State Duration Comparison (Top 10)"
    }

def get_conditions(filters):
    conditions = []
    if filters.get("workflow"):
        conditions.append("wth1.workflow = %(workflow)s")
    if filters.get("reference_doctype"):
        conditions.append("wth1.reference_doctype = %(reference_doctype)s")
    if filters.get("from_date"):
        conditions.append("DATE(wth1.transition_date) >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("DATE(wth1.transition_date) <= %(to_date)s")
    return "WHERE " + " AND ".join(conditions) if conditions else ""
