# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

# Copyright (c) 2025, CSF TZ and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    return columns, data, None, chart

def get_columns():
    return [
        {"fieldname": "reference_doctype", "label": _("DocType"), "fieldtype": "Link", "options": "DocType", "width": 120},
        {"fieldname": "reference_name", "label": _("Document"), "fieldtype": "Dynamic Link", "options": "reference_doctype", "width": 150},
        {"fieldname": "workflow", "label": _("Workflow"), "fieldtype": "Link", "options": "Workflow", "width": 120},
        {"fieldname": "state", "label": _("State"), "fieldtype": "Data", "width": 120},
        {"fieldname": "duration_hours", "label": _("Duration (Hours)"), "fieldtype": "Float", "width": 130},
        {"fieldname": "avg_duration_hours", "label": _("Avg Duration (Hours)"), "fieldtype": "Float", "width": 140},
        {"fieldname": "deviation_percentage", "label": _("Deviation (%)"), "fieldtype": "Float", "width": 120},
        {"fieldname": "duration_formatted", "label": _("Duration (Formatted)"), "fieldtype": "Data", "width": 150},
        {"fieldname": "transition_date", "label": _("Transition Date"), "fieldtype": "Datetime", "width": 150},
        {"fieldname": "user", "label": _("User"), "fieldtype": "Link", "options": "User", "width": 120}
    ]

def get_data(filters):
    conditions = get_conditions(filters)

    avg_durations = frappe.db.sql(f"""
        SELECT 
            wth1.workflow,
            wth1.current_state as state,
            AVG(
                CASE 
                    WHEN next_transition.next_date IS NOT NULL 
                    THEN TIMESTAMPDIFF(SECOND, wth1.transition_date, next_transition.next_date) / 3600.0
                    ELSE NULL
                END
            ) as avg_duration_hours
        FROM `tabWorkflow Transition History` wth1
        LEFT JOIN (
            SELECT 
                wth2.reference_name,
                wth2.transition_date as transition_point,
                MIN(wth3.transition_date) as next_date
            FROM `tabWorkflow Transition History` wth2
            LEFT JOIN `tabWorkflow Transition History` wth3 
                ON wth2.reference_name = wth3.reference_name 
                AND wth3.transition_date > wth2.transition_date
            GROUP BY wth2.reference_name, wth2.transition_date
        ) next_transition ON wth1.reference_name = next_transition.reference_name 
                         AND wth1.transition_date = next_transition.transition_point
        {conditions}
        GROUP BY wth1.workflow, wth1.current_state
        HAVING avg_duration_hours IS NOT NULL
    """, filters, as_dict=1)

    avg_lookup = {(row.workflow, row.state): row.avg_duration_hours for row in avg_durations}

    transition_data = frappe.db.sql(f"""
        SELECT 
            wth1.reference_doctype,
            wth1.reference_name,
            wth1.workflow,
            wth1.current_state as state,
            wth1.transition_date,
            wth1.user,
            CASE 
                WHEN next_transition.next_date IS NOT NULL 
                THEN TIMESTAMPDIFF(SECOND, wth1.transition_date, next_transition.next_date) / 3600.0
                ELSE NULL
            END as duration_hours
        FROM `tabWorkflow Transition History` wth1
        LEFT JOIN (
            SELECT 
                wth2.reference_name,
                wth2.transition_date as transition_point,
                MIN(wth3.transition_date) as next_date
            FROM `tabWorkflow Transition History` wth2
            LEFT JOIN `tabWorkflow Transition History` wth3 
                ON wth2.reference_name = wth3.reference_name 
                AND wth3.transition_date > wth2.transition_date
            GROUP BY wth2.reference_name, wth2.transition_date
        ) next_transition ON wth1.reference_name = next_transition.reference_name 
                         AND wth1.transition_date = next_transition.transition_point
        {conditions}
        HAVING duration_hours IS NOT NULL
        ORDER BY wth1.transition_date DESC
    """, filters, as_dict=1)

    bottlenecks = []
    threshold_percentage = filters.get("threshold_percentage", 50)

    for row in transition_data:
        key = (row.workflow, row.state)
        if key in avg_lookup:
            avg_duration = avg_lookup[key]
            if row.duration_hours > avg_duration * (1 + threshold_percentage / 100):
                deviation = ((row.duration_hours - avg_duration) / avg_duration) * 100
                bottlenecks.append({
                    'reference_doctype': row.reference_doctype,
                    'reference_name': row.reference_name,
                    'workflow': row.workflow,
                    'state': row.state,
                    'duration_hours': flt(row.duration_hours, 2),
                    'avg_duration_hours': flt(avg_duration, 2),
                    'deviation_percentage': flt(deviation, 1),
                    'duration_formatted': format_duration(row.duration_hours),
                    'transition_date': row.transition_date,
                    'user': row.user
                })

    return sorted(bottlenecks, key=lambda x: x['deviation_percentage'], reverse=True)

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

    top_bottlenecks = data[:10]
    labels = [f"{d['workflow']} → {d['state']}" for d in top_bottlenecks]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Deviation (%)",
                    "values": [d['deviation_percentage'] for d in top_bottlenecks]
                }
            ]
        },
        "type": "bar",
        "colors": ["#f44336"],
        "barOptions": {
            "horizontal": True
        },
        "title": "Top Workflow Bottlenecks by Deviation"
    }

def get_conditions(filters):
    conditions = []
    if filters.get("workflow"):
        conditions.append("wth1.workflow = %(workflow)s")
    if filters.get("reference_doctype"):
        conditions.append("wth1.reference_doctype = %(reference_doctype)s")
    if filters.get("user"):
        conditions.append("wth1.user = %(user)s")
    if filters.get("from_date"):
        conditions.append("DATE(wth1.transition_date) >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("DATE(wth1.transition_date) <= %(to_date)s")
    return "WHERE " + " AND ".join(conditions) if conditions else ""
