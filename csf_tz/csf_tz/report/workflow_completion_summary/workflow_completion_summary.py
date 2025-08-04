# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

# Copyright (c) 2025, CSF TZ and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, time_diff_in_hours, flt

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    return columns, data, None, chart

def get_columns():
    return [
        {
            "fieldname": "reference_doctype",
            "label": _("DocType"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 120
        },
        {
            "fieldname": "reference_name",
            "label": _("Document"),
            "fieldtype": "Dynamic Link",
            "options": "reference_doctype",
            "width": 150
        },
        {
            "fieldname": "workflow",
            "label": _("Workflow"),
            "fieldtype": "Link",
            "options": "Workflow",
            "width": 120
        },
        {
            "fieldname": "start_state",
            "label": _("Start State"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "current_state",
            "label": _("Current State"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "start_date",
            "label": _("Start Date"),
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "fieldname": "last_transition_date",
            "label": _("Last Transition"),
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "fieldname": "total_duration_hours",
            "label": _("Total Duration (Hours)"),
            "fieldtype": "Float",
            "width": 150
        },
        {
            "fieldname": "total_duration_formatted",
            "label": _("Duration (Formatted)"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "total_transitions",
            "label": _("Total Transitions"),
            "fieldtype": "Int",
            "width": 130
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)

    data = frappe.db.sql(f"""
        SELECT 
            reference_doctype,
            reference_name,
            workflow,
            MIN(transition_date) as start_date,
            MAX(transition_date) as last_transition_date,
            COUNT(*) as total_transitions,
            (SELECT previous_state FROM `tabWorkflow Transition History` wth2 
             WHERE wth2.reference_name = wth1.reference_name 
             ORDER BY wth2.transition_date LIMIT 1) as start_state,
            (SELECT current_state FROM `tabWorkflow Transition History` wth3 
             WHERE wth3.reference_name = wth1.reference_name 
             ORDER BY wth3.transition_date DESC LIMIT 1) as current_state
        FROM `tabWorkflow Transition History` wth1
        {conditions}
        GROUP BY reference_doctype, reference_name, workflow
        ORDER BY last_transition_date DESC
    """, filters, as_dict=1)

    # Process duration calculations for each row
    for row in data:
        if row.start_date and row.last_transition_date:
            duration_hours = time_diff_in_hours(row.last_transition_date, row.start_date)
            row.total_duration_hours = flt(duration_hours, 2)
            row.total_duration_formatted = format_duration(duration_hours)
        else:
            row.total_duration_hours = 0
            row.total_duration_formatted = "N/A"

    return data



def format_duration(hours):
    """Format duration in hours to a human-readable format"""
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes} minutes"
    elif hours < 24:
        return f"{flt(hours, 1)} hours"
    else:
        days = int(hours / 24)
        remaining_hours = int(hours % 24)
        return f"{days} days, {remaining_hours} hours"

def get_chart_data(data):
    """Generate chart data for current workflow states"""
    if not data:
        return None

    # Count by current state
    state_counts = {}
    for row in data:
        current_state = row.get('current_state', 'Unknown')
        state_counts[current_state] = state_counts.get(current_state, 0) + 1

    # Limit to top 10 states to keep chart readable
    sorted_states = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "data": {
            "labels": [state[0] for state in sorted_states],
            "datasets": [
                {
                    "name": "Documents",
                    "values": [state[1] for state in sorted_states]
                }
            ]
        },
        "type": "pie",
        "colors": ["#28a745", "#ffc107", "#dc3545", "#6c757d", "#17a2b8", "#6f42c1", "#e83e8c", "#fd7e14", "#20c997", "#6c757d"],
        "title": "Current Workflow States Distribution"
    }

def get_conditions(filters):
    conditions = []
    
    if filters.get("workflow"):
        conditions.append("wth1.workflow = %(workflow)s")
    
    if filters.get("reference_doctype"):
        conditions.append("wth1.reference_doctype = %(reference_doctype)s")
    
    if filters.get("reference_name"):
        conditions.append("wth1.reference_name = %(reference_name)s")
    
    if filters.get("from_date"):
        conditions.append("DATE(wth1.transition_date) >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("DATE(wth1.transition_date) <= %(to_date)s")

    return "WHERE " + " AND ".join(conditions) if conditions else ""