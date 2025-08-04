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
            "fieldname": "user",
            "label": _("User"),
            "fieldtype": "Link",
            "options": "User",
            "width": 150
        },
        {
            "fieldname": "full_name",
            "label": _("Full Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "total_transitions",
            "label": _("Total Transitions"),
            "fieldtype": "Int",
            "width": 130
        },
        {
            "fieldname": "unique_workflows",
            "label": _("Unique Workflows"),
            "fieldtype": "Int",
            "width": 130
        },
        {
            "fieldname": "unique_documents",
            "label": _("Unique Documents"),
            "fieldtype": "Int",
            "width": 130
        },
        {
            "fieldname": "avg_transitions_per_day",
            "label": _("Avg Transitions/Day"),
            "fieldtype": "Float",
            "width": 140
        },
        {
            "fieldname": "workflows",
            "label": _("Workflows"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "first_transition",
            "label": _("First Transition"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "last_transition",
            "label": _("Last Transition"),
            "fieldtype": "Date",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Get user activity data
    data = frappe.db.sql(f"""
        SELECT 
            wth.user,
            u.full_name,
            COUNT(*) as total_transitions,
            COUNT(DISTINCT wth.workflow) as unique_workflows,
            COUNT(DISTINCT wth.reference_name) as unique_documents,
            GROUP_CONCAT(DISTINCT wth.workflow SEPARATOR ', ') as workflows,
            MIN(DATE(wth.transition_date)) as first_transition,
            MAX(DATE(wth.transition_date)) as last_transition,
            DATEDIFF(MAX(DATE(wth.transition_date)), MIN(DATE(wth.transition_date))) + 1 as active_days
        FROM `tabWorkflow Transition History` wth
        LEFT JOIN `tabUser` u ON wth.user = u.name
        {conditions}
        GROUP BY wth.user, u.full_name
        ORDER BY total_transitions DESC
    """, filters, as_dict=1)
    
    # Calculate average transitions per day
    for row in data:
        if row.active_days and row.active_days > 0:
            row.avg_transitions_per_day = flt(row.total_transitions / row.active_days, 2)
        else:
            row.avg_transitions_per_day = 0
    
    return data

def get_chart_data(data):
    """Generate chart data for user activity visualization"""
    if not data:
        return None
    
    # Get top 10 users by transitions
    top_users = data[:10]
    
    return {
        "data": {
            "labels": [d.get("full_name") or d.get("user") for d in top_users],
            "datasets": [
                {
                    "name": "Total Transitions",
                    "values": [d.get("total_transitions", 0) for d in top_users]
                }
            ]
        },
        "type": "bar",
        "colors": ["#7cd6fd"],
        "title": "Top Users by Workflow Transitions"
    }

def get_conditions(filters):
    conditions = []
    
    if filters.get("user"):
        conditions.append("wth.user = %(user)s")
    
    if filters.get("workflow"):
        conditions.append("wth.workflow = %(workflow)s")
    
    if filters.get("reference_doctype"):
        conditions.append("wth.reference_doctype = %(reference_doctype)s")
    
    if filters.get("from_date"):
        conditions.append("DATE(wth.transition_date) >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("DATE(wth.transition_date) <= %(to_date)s")
    
    return "WHERE " + " AND ".join(conditions) if conditions else ""