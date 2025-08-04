# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

# Copyright (c) 2025, CSF TZ and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, time_diff_in_hours, flt, format_date

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    return columns, data, None, chart

def get_columns():
    return [
        {
            "fieldname": "date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "day_of_week",
            "label": _("Day"),
            "fieldtype": "Data",
            "width": 80
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
            "fieldname": "unique_users",
            "label": _("Active Users"),
            "fieldtype": "Int",
            "width": 110
        },
        {
            "fieldname": "peak_hour",
            "label": _("Peak Hour"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "peak_hour_transitions",
            "label": _("Peak Hour Count"),
            "fieldtype": "Int",
            "width": 130
        },
        {
            "fieldname": "workflows_list",
            "label": _("Workflows"),
            "fieldtype": "Data",
            "width": 200
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Get daily activity summary
    daily_data = frappe.db.sql(f"""
        SELECT 
            DATE(transition_date) as date,
            DAYNAME(transition_date) as day_of_week,
            COUNT(*) as total_transitions,
            COUNT(DISTINCT workflow) as unique_workflows,
            COUNT(DISTINCT reference_name) as unique_documents,
            COUNT(DISTINCT user) as unique_users,
            GROUP_CONCAT(DISTINCT workflow SEPARATOR ', ') as workflows_list
        FROM `tabWorkflow Transition History`
        {conditions}
        GROUP BY DATE(transition_date)
        ORDER BY date DESC
    """, filters, as_dict=1)
    
    # Get peak hour data for each date
    for row in daily_data:
        peak_hour_data = frappe.db.sql("""
            SELECT 
                HOUR(transition_date) as hour,
                COUNT(*) as hour_count
            FROM `tabWorkflow Transition History`
            WHERE DATE(transition_date) = %s
            GROUP BY HOUR(transition_date)
            ORDER BY hour_count DESC
            LIMIT 1
        """, (row.date,), as_dict=1)
        
        if peak_hour_data:
            peak_hour = peak_hour_data[0].hour
            row.peak_hour = f"{peak_hour:02d}:00-{peak_hour+1:02d}:00"
            row.peak_hour_transitions = peak_hour_data[0].hour_count
        else:
            row.peak_hour = "N/A"
            row.peak_hour_transitions = 0
    
    return daily_data

def get_chart_data(data):
    """Generate chart data for daily activity visualization"""
    if not data:
        return None
    
    # Sort by date for time series
    sorted_data = sorted(data, key=lambda x: x['date'])
    
    return {
        "data": {
            "labels": [format_date(d['date']) for d in sorted_data],
            "datasets": [
                {
                    "name": "Daily Transitions",
                    "values": [d['total_transitions'] for d in sorted_data]
                },
                {
                    "name": "Active Users",
                    "values": [d['unique_users'] for d in sorted_data]
                }
            ]
        },
        "type": "line",
        "colors": ["#7cd6fd", "#ff6384"],
        "title": "Daily Workflow Activity Trend"
    }

def get_conditions(filters):
    conditions = []
    
    if filters.get("workflow"):
        conditions.append("workflow = %(workflow)s")
    
    if filters.get("reference_doctype"):
        conditions.append("reference_doctype = %(reference_doctype)s")
    
    if filters.get("user"):
        conditions.append("user = %(user)s")
    
    if filters.get("from_date"):
        conditions.append("DATE(transition_date) >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("DATE(transition_date) <= %(to_date)s")
    else:
        # Default to last 30 days if no date range specified
        conditions.append("DATE(transition_date) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)")
    
    return "WHERE " + " AND ".join(conditions) if conditions else "WHERE DATE(transition_date) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"