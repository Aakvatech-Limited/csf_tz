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
            "fieldname": "workflow",
            "label": _("Workflow"),
            "fieldtype": "Link",
            "options": "Workflow",
            "width": 150
        },
        {
            "fieldname": "from_state",
            "label": _("From State"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "to_state",
            "label": _("To State"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "transition_count",
            "label": _("Transition Count"),
            "fieldtype": "Int",
            "width": 130
        },
        {
            "fieldname": "percentage_of_workflow",
            "label": _("% of Workflow"),
            "fieldtype": "Float",
            "width": 120
        },
        {
            "fieldname": "avg_duration_hours",
            "label": _("Avg Duration (Hours)"),
            "fieldtype": "Float",
            "width": 140
        },
        {
            "fieldname": "avg_duration_formatted",
            "label": _("Avg Duration (Formatted)"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "unique_documents",
            "label": _("Unique Documents"),
            "fieldtype": "Int",
            "width": 130
        },
        {
            "fieldname": "unique_users",
            "label": _("Unique Users"),
            "fieldtype": "Int",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Get transition frequency data with durations
    data = frappe.db.sql(f"""
        SELECT 
            wth1.workflow,
            wth1.previous_state as from_state,
            wth1.current_state as to_state,
            COUNT(*) as transition_count,
            COUNT(DISTINCT wth1.reference_name) as unique_documents,
            COUNT(DISTINCT wth1.user) as unique_users,
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
        GROUP BY wth1.workflow, wth1.previous_state, wth1.current_state
        ORDER BY wth1.workflow, transition_count DESC
    """, filters, as_dict=1)
    
    # Calculate percentages per workflow
    workflow_totals = {}
    for row in data:
        workflow = row.workflow
        if workflow not in workflow_totals:
            workflow_totals[workflow] = 0
        workflow_totals[workflow] += row.transition_count
    
    # Add percentage calculations and format durations
    for row in data:
        workflow = row.workflow
        if workflow_totals.get(workflow, 0) > 0:
            row.percentage_of_workflow = flt((row.transition_count / workflow_totals[workflow]) * 100, 2)
        else:
            row.percentage_of_workflow = 0
        
        if row.avg_duration_hours:
            row.avg_duration_hours = flt(row.avg_duration_hours, 2)
            row.avg_duration_formatted = format_duration(row.avg_duration_hours)
        else:
            row.avg_duration_hours = 0
            row.avg_duration_formatted = "N/A"
    
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
    """Generate chart data for transition frequency visualization"""
    if not data:
        return None
    
    # Get top 10 most frequent transitions
    top_transitions = sorted(data, key=lambda x: x['transition_count'], reverse=True)[:10]
    
    labels = [f"{d['from_state']} → {d['to_state']}" for d in top_transitions]
    
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Transition Count",
                    "values": [d['transition_count'] for d in top_transitions]
                }
            ]
        },
        "type": "bar",
        "colors": ["#36a2eb"],
        "title": "Most Frequent Workflow Transitions"
    }

def get_conditions(filters):
    conditions = []
    
    if filters.get("workflow"):
        conditions.append("wth1.workflow = %(workflow)s")
    
    if filters.get("reference_doctype"):
        conditions.append("wth1.reference_doctype = %(reference_doctype)s")
    
    if filters.get("from_state"):
        conditions.append("wth1.previous_state = %(from_state)s")
    
    if filters.get("to_state"):
        conditions.append("wth1.current_state = %(to_state)s")
    
    if filters.get("from_date"):
        conditions.append("DATE(wth1.transition_date) >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("DATE(wth1.transition_date) <= %(to_date)s")
    
    return "WHERE " + " AND ".join(conditions) if conditions else ""
