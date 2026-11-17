# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

import frappe
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from frappe import msgprint, _
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Count, Date, DateFormat, Max, Min
from frappe.utils.nestedset import get_descendants_of
from frappe.utils import cstr, cint, get_time, add_to_date, getdate


def execute(filters=None):
    conditions, filters = get_conditions(filters)

    columns = get_columns(filters)

    chift_type_details = frappe.get_all("Shift Type", {"enable_auto_attendance": 1},
        ["name", "start_time", "end_time", "late_entry_grace_period", "early_exit_grace_period"]
    )

    data = []
    checkin_records = get_checkin_data(conditions, filters, chift_type_details)
    checkout_records = get_checkout_data(conditions, filters, chift_type_details)

    if checkin_records and checkout_records:
        # Create dataframes for merging
        checkin_colnames = [key for key in checkin_records[0].keys()]
        checkin_data = pd.DataFrame.from_records(
            checkin_records, columns=checkin_colnames
        )

        checkout_colnames = [key for key in checkout_records[0].keys()]
        checkout_data = pd.DataFrame.from_records(
            checkout_records, columns=checkout_colnames
        )

        # Merge the check-in and check-out data on common columns
        df = checkin_data.merge(
            checkout_data,
            how="outer",
            on=["employee", "employee_name", "department", "shift", "date", "week_day"]
        )
        df.fillna("", inplace=True)

        # Calculate Total Hours Spent
        def calc_total_hours(row):
            try:
                if row["checkin_time"] and row["checkout_time"]:
                    t1 = datetime.strptime(row["checkin_time"], "%H:%M:%S")
                    t2 = datetime.strptime(row["checkout_time"], "%H:%M:%S")
                    delta = t2 - t1
                    if delta.days < 0:
                        delta = timedelta(days=0, seconds=delta.seconds, microseconds=delta.microseconds)
                    return str(delta)
                else:
                    return ""
            except Exception:
                return ""
        df["total_hours_spent"] = df.apply(calc_total_hours, axis=1)

        # Sort the dataframe by date first, then by employee
        df = df.sort_values(by=["date", "employee"])

        # Add the sorted data to the result
        data += df.values.tolist()

    elif checkin_records or checkout_records:
        # Handle cases where only one of check-in or check-out data exists
        if checkin_records:
            checkin_data = pd.DataFrame.from_records(checkin_records)
            checkin_data["total_hours_spent"] = ""
            checkin_data = checkin_data.sort_values(by=["date", "employee"])
            data += checkin_data.values.tolist()

        if checkout_records:
            checkout_data = pd.DataFrame.from_records(checkout_records)
            checkout_data["total_hours_spent"] = ""
            checkout_data = checkout_data.sort_values(by=["date", "employee"])
            data += checkout_data.values.tolist()

    else:
        # No records found for the filters
        msgprint(
            "No Record found for the filters From Date: {0}, To Date: {1}, Company: {2}, Department: {3}, and Employee: {4}\
            you specified...!!! Please set different filters and Try again..!!!".format(
                frappe.bold(filters.from_date),
                frappe.bold(filters.to_date),
                frappe.bold(filters.company),
                frappe.bold(filters.department),
                frappe.bold(filters.employee),
            )
        )

    return columns, data

def get_columns(filters):
    columns = [
        {"fieldname": "employee", "label": _("Employee No"), "fieldtype": "Link", "options": "Employee", "width": 155},
        {"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data"},
        {"fieldname": "department", "label": _("Department"), "fieldtype": "Link", "options": "Department"},
        {"fieldname": "shift", "label": _("Shift"), "fieldtype": "Link", "options": "Shift Type"},
        {"fieldname": "date", "label": _("Date"), "fieldtype": "Date"},
        {"fieldname": "week_day", "label": _("Week Day "), "fieldtype": "Data"},

        # for checkin
        {"fieldname": "actual_checkin_time", "label": _("Actual Time to Checkin"), "fieldtype": "Time"},
        {"fieldname": "checkin_time", "label": _("Checkin Time"), "fieldtype": "Time"},
        {"fieldname": "late_entry_grace_time", "label": _("Late Entry Grace Period"), "fieldtype": "Time"},
        {"fieldname": "checkin_status", "label": _("Checkin Status"), "fieldtype": "Data"},

        # for checkout
        {"fieldname": "actual_checkout_time", "label": _("Actual Time to Checkout"), "fieldtype": "Time"},
        {"fieldname": "checkout_time", "label": _("Checkout Time"), "fieldtype": "Time"},
        {"fieldname": "early_exit_grace_time", "label": _("Early Exit Grace Period"), "fieldtype": "Time"},
        {"fieldname": "checkout_status", "label": _("Checkout Status"), "fieldtype": "Data"},
        # Add Total Hours Spent as the last column
        {"fieldname": "total_hours_spent", "label": _("Total Hours Spent"), "fieldtype": "Data", "width": 120},
    ]
    return columns

def get_conditions(filters):
    checkin = frappe.qb.DocType("Employee Checkin")
    employee = frappe.qb.DocType("Employee")
    conditions = []
    if filters.get("from_date"):
        conditions.append(Date(checkin.time) >= filters.get("from_date"))
    if filters.get("to_date"):
        conditions.append(Date(checkin.time) <= filters.get("to_date"))
    if filters.get("company"):
        conditions.append(employee.company == filters.get("company"))
    if filters.get("department") and filters.get("company"):
        department_list = get_department(
            filters.get("department"), filters.get("company")
        )
        conditions.append(employee.department.isin(department_list))
    if filters.get("employee"):
        conditions.append(checkin.employee == filters.get("employee"))
    return conditions, filters

def get_department(department, company):
    department_list = get_descendants_of("Department", department)
    department_list.append(department)
    return department_list

def get_checkin_data(conditions, filters, chift_type_details):
    checkin_data = []
    checkin_details = get_checkin_details(conditions, filters)
    
    for checkin_d in checkin_details:
        if checkin_d.default_shift and checkin_d.shift_type:
            checkin_d["shift"] = checkin_d.shift_type

        if checkin_d.default_shift or checkin_d.shift_type:
            checkin_d["shift"] = checkin_d.shift_type or checkin_d.default_shift

        if checkin_d.shift:
            for shift_type in chift_type_details:
                if checkin_d.shift == shift_type.name:
                    checkin_time_diff = get_time(checkin_d.checkin_time)

                    late_entry_grace_time = str("00:" + cstr(shift_type.late_entry_grace_period) + ":00")
                    start_time = get_time(str(shift_type.start_time))

                    start_time_diff = get_time(add_to_date(str(shift_type.start_time), minutes=shift_type.late_entry_grace_period, as_string=False, as_datetime=True))
                    
                    if checkin_time_diff <= start_time:
                        checkin_status = "Early Checkin"
                    else:
                        if checkin_time_diff <= start_time_diff:
                            checkin_status = "On Time"
                        else:
                            checkin_status = "Late Checkin"

                    complete_row = {
                        "employee": checkin_d.employee,
                        "employee_name": checkin_d.employee_name,
                        "department": checkin_d.department,
                        "shift": checkin_d.shift,
                        "date": checkin_d.date,
                        "week_day": getdate(checkin_d.date).strftime("%A"),
                        "actual_checkin_time": str(shift_type.start_time),
                        "checkin_time": checkin_d.checkin_time,
                        "late_entry_grace_time": late_entry_grace_time,
                        "checkin_status": checkin_status
                    }

                    checkin_data.append(complete_row)

                else:
                    continue
        
        else:
            half_row = {
                "employee": checkin_d.employee,
                "employee_name": checkin_d.employee_name,
                "department": checkin_d.department,
                "shift": '',
                "date": checkin_d.date,
                "week_day": getdate(checkin_d.date).strftime("%A"),
                "actual_checkin_time": '',
                "checkin_time": checkin_d.checkin_time,
                "late_entry_grace_time": '',
                "checkin_status": ''
            }

            checkin_data.append(half_row)
    
    return checkin_data

def get_checkout_data(conditions, filters, chift_type_details):
    checkout_data = []
    checkout_details = get_checkout_details(conditions, filters)
    
    for checkout_d in checkout_details:
        if checkout_d.default_shift and checkout_d.shift_type:
            checkout_d["shift"] = checkout_d.shift_type

        if checkout_d.default_shift or checkout_d.shift_type:
            checkout_d["shift"] = checkout_d.shift_type or checkout_d.default_shift

        if checkout_d.shift:
            for shift_type in chift_type_details:
                if checkout_d.shift == shift_type.name:
                    checkout_time_diff = get_time(checkout_d.checkout_time)

                    early_exit_grace_time = str("00:" + cstr(shift_type.early_exit_grace_period) + ":00")
                    end_time = get_time(str(shift_type.end_time))

                    end_time_diff = get_time(add_to_date(str(shift_type.end_time), minutes=(- + (shift_type.early_exit_grace_period)), as_string=False, as_datetime=True))
                    
                    if checkout_time_diff <= end_time_diff:
                        checkout_status = "Early Checkout"
                    else:
                        if checkout_time_diff <= end_time:
                            checkout_status = "On Time"
                        else:
                            checkout_status = "Late Checkout"

                    complete_row = {
                        "employee": checkout_d.employee,
                        "employee_name": checkout_d.employee_name,
                        "department": checkout_d.department,
                        "shift": checkout_d.shift,
                        "date": checkout_d.date,
                        "week_day": getdate(checkout_d.date).strftime("%A"),
                        "actual_checkout_time":  str(shift_type.end_time),
                        "checkout_time": checkout_d.checkout_time,
                        "early_exit_grace_time": early_exit_grace_time,
                        "checkout_status": checkout_status
                    }
                    
                    checkout_data.append(complete_row)

                else:
                    continue
        
        else:
            half_row = {
                "employee": checkout_d.employee,
                "employee_name": checkout_d.employee_name,
                "department": checkout_d.department,
                "shift": '',
                "date": checkout_d.date,
                "week_day": getdate(checkout_d.date).strftime("%A"),
                "actual_checkout_time": '',
                "checkout_time": checkout_d.checkout_time,
                "early_exit_grace_time": '',
                "checkout_status": ''
            }

            checkout_data.append(half_row)
    
    return checkout_data

def get_checkin_details(conditions, filters):
    checkin = frappe.qb.DocType("Employee Checkin")
    data = (
        get_daily_checkin_query(conditions, filters, "IN")
        .select(Min(DateFormat(checkin.time, "%T")).as_("checkin_time"))
        .run(as_dict=True)
    )
    return data


def get_checkout_details(conditions, filters):
    checkin = frappe.qb.DocType("Employee Checkin")
    data = (
        get_daily_checkin_query(conditions, filters, "OUT")
        .select(Max(DateFormat(checkin.time, "%T")).as_("checkout_time"))
        .run(as_dict=True)
    )
    return data


def get_daily_checkin_query(conditions, filters, log_type):
    checkin = frappe.qb.DocType("Employee Checkin")
    employee = frappe.qb.DocType("Employee")
    shift_assignment = frappe.qb.DocType("Shift Assignment")
    return (
        frappe.qb.from_(checkin)
        .inner_join(employee)
        .on(employee.name == checkin.employee)
        .left_join(shift_assignment)
        .on(
            (checkin.employee == shift_assignment.employee)
            & shift_assignment.start_date.between(filters["from_date"], filters["to_date"])
            & Date(checkin.time).between(shift_assignment.start_date, shift_assignment.end_date)
        )
        .select(
            checkin.employee,
            checkin.employee_name,
            employee.department,
            employee.default_shift,
            shift_assignment.shift_type,
            DateFormat(checkin.time, "%Y-%m-%d").as_("date"),
        )
        .where(checkin.log_type == log_type)
        .where(Criterion.all(conditions))
        .groupby(checkin.employee, Date(checkin.time))
        .orderby(Date(checkin.time))
        .orderby(checkin.employee)
    )

def get_today_summary():
    today = frappe.utils.today()
    in_count = get_checkin_count("IN", today)
    out_count = get_checkin_count("OUT", today)
    return {
        "date": today,
        "in_count": in_count,
        "out_count": out_count
    }

def get_checkin_count(log_type, date):
    checkin = frappe.qb.DocType("Employee Checkin")
    return (
        frappe.qb.from_(checkin)
        .select(Count("*"))
        .where((checkin.log_type == log_type) & (Date(checkin.time) == date))
        .run()[0][0]
    )

@frappe.whitelist()
def get_employee_checkin_summary():
    return get_today_summary()