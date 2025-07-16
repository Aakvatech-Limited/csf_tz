# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt


import frappe
import erpnext
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import get_descendants_of


salary_slip = frappe.qb.DocType("Salary Slip")
salary_detail = frappe.qb.DocType("Salary Detail")
salary_component = frappe.qb.DocType("Salary Component")


def execute(filters=None):
    if not filters:
        filters = {}
    currency = None
    if filters.get("currency"):
        currency = filters.get("currency")
    company_currency = erpnext.get_company_currency(filters.get("company"))

    if currency and currency == company_currency and filters.get("multi_currency"):
        frappe.throw(
            _(
                f"Currency: <b>{currency}</b> on report filters and default company currency: <b>{company_currency}</b> cannot be same for Multi Currency Report, please change one of them."
            )
        )

    salary_slips = get_salary_slips(filters)
    if not salary_slips:
        frappe.msgprint("<b>No record found for the filters above</b>")
        return [], []

    return get_data(filters, salary_slips, currency, company_currency)


def get_data(filters, salary_slips, currency, company_currency):
    earning_types, ded_types = get_earning_and_deduction_types(salary_slips)
    columns = get_columns(filters, company_currency, earning_types, ded_types)

    ss_earning_map = get_salary_slip_details(
        salary_slips, currency, company_currency, "earnings"
    )
    ss_ded_map = get_salary_slip_details(
        salary_slips, currency, company_currency, "deductions"
    )

    doj_map = get_employee_doj_map()

    data = []
    replace_currency_label = False
    unique_columns = [column.get("fieldname") for column in columns]
    for ss in salary_slips:
        row = {
            "salary_slip_id": ss.name,
            "employee": ss.employee,
            "employee_name": ss.employee_name,
            "data_of_joining": doj_map.get(ss.employee),
            "branch": ss.branch,
            "department": ss.department,
            "designation": ss.designation,
            "company": ss.company,
            "start_date": ss.start_date,
            "end_date": ss.end_date,
            "payment_days": ss.payment_days,
            "currency": ss.currency,
            "docstatus": get_status_display(ss.docstatus),
            "workflow_state": getattr(ss, "workflow_state", None)
            or get_default_workflow_state(ss.docstatus),
        }
        if filters.get("multi_currency") and ss.currency != company_currency:
            row["exchange_rate"] = ss.exchange_rate

            if "exchange_rate" not in unique_columns:
                columns.append(
                    {
                        "label": _("Exchange Rate"),
                        "fieldname": "exchange_rate",
                        "fieldtype": "Float",
                        "width": 120,
                    }
                )
                unique_columns.append("exchange_rate")

        row["leave_without_pay"] = ss.leave_without_pay
        if "leave_without_pay" not in unique_columns:
            columns.append(
                {
                    "label": _("Leave Without Pay"),
                    "fieldname": "leave_without_pay",
                    "fieldtype": "Currency",
                    "options": "currency",
                    "width": 100,
                }
            )
            unique_columns.append("leave_without_pay")

        if filters.get("multi_currency") and ss.currency != company_currency:
            row["leave_without_pay_" + str(company_currency).lower()] = flt(
                ss.leave_without_pay
            ) * flt(ss.exchange_rate)

            if (
                "leave_without_pay_" + str(company_currency).lower()
                not in unique_columns
            ):
                columns.append(
                    {
                        "label": _(f"Leave Without Pay {company_currency}"),
                        "fieldname": "leave_without_pay_"
                        + str(company_currency).lower(),
                        "fieldtype": "Currency",
                        "options": "company_currency",
                        "width": 120,
                    }
                )
                unique_columns.append(
                    "leave_without_pay_" + str(company_currency).lower()
                )

        update_column_width(ss, columns)

        for e in earning_types:
            row.update({frappe.scrub(e): ss_earning_map.get(ss.name, {}).get(e)})
            if frappe.scrub(e) not in unique_columns:
                columns.append(
                    {
                        "label": e,
                        "fieldname": frappe.scrub(e),
                        "fieldtype": "Currency",
                        "options": "currency",
                        "width": 120,
                    }
                )
                unique_columns.append(frappe.scrub(e))

            if filters.get("multi_currency") and ss.currency != company_currency:
                e_amount = ss_earning_map.get(ss.name, {}).get(e) or 0
                row.update(
                    {
                        frappe.scrub(e)
                        + "_"
                        + str(company_currency).lower(): e_amount
                        * flt(ss.exchange_rate)
                    }
                )

                if (
                    frappe.scrub(e) + "_" + str(company_currency).lower()
                    not in unique_columns
                ):
                    columns.append(
                        {
                            "label": e + " " + str(company_currency),
                            "fieldname": frappe.scrub(e)
                            + "_"
                            + str(company_currency).lower(),
                            "fieldtype": "Currency",
                            "options": "company_currency",
                            "width": 120,
                        }
                    )
                    unique_columns.append(
                        frappe.scrub(e) + "_" + str(company_currency).lower()
                    )

        row["gross_pay"] = ss.gross_pay
        if "gross_pay" not in unique_columns:
            columns.append(
                {
                    "label": _("Gross Pay"),
                    "fieldname": "gross_pay",
                    "fieldtype": "Currency",
                    "options": "currency",
                    "width": 120,
                }
            )
            unique_columns.append("gross_pay")

        if filters.get("multi_currency") and ss.currency != company_currency:
            row.update(
                {
                    "gross_pay_"
                    + str(company_currency).lower(): flt(ss.gross_pay)
                    * flt(ss.exchange_rate),
                }
            )

            if "gross_pay_" + str(company_currency).lower() not in unique_columns:
                columns.append(
                    {
                        "label": _(f"Gross Pay {company_currency}"),
                        "fieldname": "gross_pay_" + str(company_currency).lower(),
                        "fieldtype": "Currency",
                        "options": "company_currency",
                        "width": 120,
                    }
                )
                unique_columns.append("gross_pay_" + str(company_currency).lower())

        for d in ded_types:
            row.update({frappe.scrub(d): ss_ded_map.get(ss.name, {}).get(d)})
            if frappe.scrub(d) not in unique_columns:
                columns.append(
                    {
                        "label": d,
                        "fieldname": frappe.scrub(d),
                        "fieldtype": "Currency",
                        "options": "currency",
                        "width": 120,
                    }
                )
                unique_columns.append(frappe.scrub(d))

            if filters.get("multi_currency") and ss.currency != company_currency:
                d_amount = ss_ded_map.get(ss.name, {}).get(d) or 0
                row.update(
                    {
                        frappe.scrub(d)
                        + "_"
                        + str(company_currency).lower(): d_amount
                        * flt(ss.exchange_rate)
                    }
                )
                if (
                    frappe.scrub(d) + "_" + str(company_currency).lower()
                    not in unique_columns
                ):
                    columns.append(
                        {
                            "label": d + " " + str(company_currency),
                            "fieldname": frappe.scrub(d)
                            + "_"
                            + str(company_currency).lower(),
                            "fieldtype": "Currency",
                            "options": "company_currency",
                            "width": 120,
                        }
                    )
                    unique_columns.append(
                        frappe.scrub(d) + "_" + str(company_currency).lower()
                    )

        row.update(
            {
                "loan_repayment": ss.total_loan_repayment,
                "total_deduction": ss.total_deduction,
                "net_pay": ss.net_pay,
            }
        )
        if filters.get("multi_currency") and ss.currency != company_currency:
            row.update(
                {
                    "loan_repayment_"
                    + str(company_currency).lower(): flt(ss.total_loan_repayment)
                    * flt(ss.exchange_rate),
                    "total_deduction_"
                    + str(company_currency).lower(): flt(ss.total_deduction)
                    * flt(ss.exchange_rate),
                    "net_pay_"
                    + str(company_currency).lower(): flt(ss.net_pay)
                    * flt(ss.exchange_rate),
                }
            )

        for field in ["loan_repayment", "total_deduction", "net_pay"]:
            if field not in unique_columns:
                columns.append(
                    {
                        "label": _(frappe.unscrub(field)),
                        "fieldname": field,
                        "fieldtype": "Currency",
                        "options": "currency",
                        "width": 120,
                    }
                )
                unique_columns.append(field)

            if filters.get("multi_currency") and ss.currency != company_currency:
                report_fieldname = field + "_" + str(company_currency).lower()
                if report_fieldname not in unique_columns:
                    columns.append(
                        {
                            "label": _(f"{frappe.unscrub(field)} {company_currency}"),
                            "fieldname": report_fieldname,
                            "fieldtype": "Currency",
                            "options": "company_currency",
                            "width": 120,
                        }
                    )
                    unique_columns.append(report_fieldname)

        data.append(row)

        if not replace_currency_label:
            for col in columns:
                if (
                    # col.get("options") == "currency"
                    company_currency
                    in col["label"]
                ):
                    col["label"] = col["label"].replace(ss.currency, "")
            replace_currency_label = True

    return columns, data


def get_earning_and_deduction_types(salary_slips):
    salary_component_and_type = {_("Earning"): [], _("Deduction"): []}
    salary_components = get_salary_components(salary_slips)

    for component in salary_components:
        component_type = get_salary_component_type(component.salary_component)
        salary_component_and_type[_(component_type)].append(component.salary_component)
    return sorted(salary_component_and_type[_("Earning")]), sorted(
        salary_component_and_type[_("Deduction")]
    )


def update_column_width(ss, columns):
    if ss.branch is not None:
        columns[3].update({"width": 120})
    if ss.department is not None:
        columns[4].update({"width": 120})
    if ss.designation is not None:
        columns[5].update({"width": 120})
    if ss.leave_without_pay is not None:
        columns[9].update({"width": 120})


def get_columns(filters, company_currency, earning_types, ded_types):
    columns = [
        {
            "label": _("Salary Slip ID"),
            "fieldname": "salary_slip_id",
            "fieldtype": "Link",
            "options": "Salary Slip",
            "width": 150,
        },
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("Date of Joining"),
            "fieldname": "data_of_joining",
            "fieldtype": "Date",
            "width": 80,
        },
        {
            "label": _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Link",
            "options": "Branch",
            "width": -1,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": -1,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Link",
            "options": "Designation",
            "width": 120,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 120,
        },
        {
            "label": _("Start Date"),
            "fieldname": "start_date",
            "fieldtype": "Date",
            "width": 80,
        },
        {
            "label": _("End Date"),
            "fieldname": "end_date",
            "fieldtype": "Date",
            "width": 80,
        },
        # {
        #     "label": _("Currency"),
        #     "fieldtype": "Link",
        #     "fieldname": "currency",
        #     "options": "Currency",
        #     "hidden": 1,
        # },
        {
            "label": _("Payment Days"),
            "fieldname": "payment_days",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": _("Status"),
            "fieldname": "docstatus",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Workflow State"),
            "fieldname": "workflow_state",
            "fieldtype": "Data",
            "width": 120,
        },
    ]
    return columns


def get_salary_components(salary_slips):
    return (
        frappe.qb.from_(salary_detail)
        .where(
            (salary_detail.amount != 0)
            & (salary_detail.parent.isin([d.name for d in salary_slips]))
        )
        .select(salary_detail.salary_component)
        .distinct()
    ).run(as_dict=True)


def get_salary_component_type(salary_component):
    return frappe.db.get_value("Salary Component", salary_component, "type", cache=True)


def get_salary_slips(filters):
    doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

    query = frappe.qb.from_(salary_slip).select(salary_slip.star)

    if filters.get("docstatus"):
        query = query.where(
            salary_slip.docstatus == doc_status[filters.get("docstatus")]
        )

    if filters.get("from_date"):
        query = query.where(salary_slip.start_date >= filters.get("from_date"))

    if filters.get("to_date"):
        query = query.where(salary_slip.end_date <= filters.get("to_date"))

    if filters.get("company"):
        query = query.where(salary_slip.company == filters.get("company"))

    if filters.get("employee"):
        query = query.where(salary_slip.employee == filters.get("employee"))

    if filters.get("currency") and filters.get("currency"):
        query = query.where(salary_slip.currency == filters.get("currency"))
    if filters.get("department") and filters.get("company"):
        department_list = get_departments(
            filters.get("department"), filters.get("company")
        )
        query = query.where(salary_slip.department.isin(department_list))

    salary_slips = query.run(as_dict=1)

    return salary_slips or []


def get_employee_doj_map():
    employee = frappe.qb.DocType("Employee")

    result = (
        frappe.qb.from_(employee).select(employee.name, employee.date_of_joining)
    ).run()

    return frappe._dict(result)


def get_salary_slip_details(salary_slips, currency, company_currency, component_type):
    salary_slips = [ss.name for ss in salary_slips]

    result = (
        frappe.qb.from_(salary_slip)
        .join(salary_detail)
        .on(salary_slip.name == salary_detail.parent)
        .where(
            (salary_detail.parent.isin(salary_slips))
            & (salary_detail.parentfield == component_type)
        )
        .select(
            salary_detail.parent,
            salary_detail.salary_component,
            salary_detail.amount,
            salary_slip.exchange_rate,
        )
    ).run(as_dict=1)

    ss_map = {}

    for d in result:
        ss_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
        if currency == company_currency:
            ss_map[d.parent][d.salary_component] += flt(d.amount) * flt(
                d.exchange_rate if d.exchange_rate else 1
            )
        else:
            ss_map[d.parent][d.salary_component] += flt(d.amount)

    return ss_map


def get_departments(department, company):
    departments_list = get_descendants_of("Department", department)
    departments_list.append(department)
    return departments_list


def get_status_display(docstatus):
    """Convert docstatus to human readable format"""
    status_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
    return status_map.get(docstatus, "Unknown")


def get_default_workflow_state(docstatus):
    """Get default workflow state based on docstatus"""
    if docstatus == 0:
        return "Draft"
    elif docstatus == 1:
        return "Approved"
    elif docstatus == 2:
        return "Cancelled"
    return "Unknown"


def is_approvable(docstatus, workflow_state, workflow_info=None):
    """Check if a salary slip can be approved using dynamic workflow states"""
    # Draft documents can always be approved if no workflow
    if docstatus == 0 and not workflow_info:
        return True

    # Get workflow info if not provided
    if not workflow_info:
        workflow_info = get_workflow_info()

    # If no workflow, only draft documents can be approved
    if not workflow_info.get("has_workflow"):
        return docstatus == 0

    # Check if current workflow state is in approvable states
    approvable_states = workflow_info.get("approvable_states", [])

    # If workflow state is in approvable states
    if workflow_state and workflow_state in approvable_states:
        return True

    # If no workflow state but document is draft, it might be approvable
    if not workflow_state and docstatus == 0:
        return True

    return False


def get_cached_workflow_info():
    """Get cached workflow info to avoid repeated calls"""
    cache_key = "salary_slip_workflow_info"
    workflow_info = frappe.cache().get_value(cache_key)

    if not workflow_info:
        workflow_info = get_workflow_info()
        # Cache for 5 minutes
        frappe.cache().set_value(cache_key, workflow_info, expires_in_sec=300)

    return workflow_info


@frappe.whitelist()
def get_workflow_info():
    """Get dynamic workflow information for Salary Slip doctype"""
    from frappe.model.workflow import get_workflow_name

    try:
        workflow_name = get_workflow_name("Salary Slip")
        if not workflow_name:
            return {
                "has_workflow": False,
                "approvable_states": ["Draft"],  # Default for non-workflow
                "approval_actions": ["Submit"],
            }

        workflow_doc = frappe.get_doc("Workflow", workflow_name)

        # Get all states that can transition to an approved/submitted state
        approvable_states = []
        approval_actions = set()

        # Find states that have outgoing transitions (can be acted upon)
        for transition in workflow_doc.transitions:
            # States that can transition are potentially approvable
            approvable_states.append(transition.state)
            approval_actions.add(transition.action)

        # Remove duplicates and get unique approvable states
        approvable_states = list(set(approvable_states))
        approval_actions = list(approval_actions)

        # Filter out final states (states with no outgoing transitions)
        final_states = []

        for state in workflow_doc.states:
            if state.state not in [t.state for t in workflow_doc.transitions]:
                final_states.append(state.state)

        # Remove final states from approvable states
        approvable_states = [
            state for state in approvable_states if state not in final_states
        ]

        return {
            "has_workflow": True,
            "workflow_name": workflow_name,
            "approvable_states": approvable_states,
            "approval_actions": approval_actions,
            "all_states": [state.state for state in workflow_doc.states],
        }

    except Exception as e:
        frappe.log_error(f"Error getting workflow info: {str(e)}")
        return {
            "has_workflow": False,
            "approvable_states": ["Draft"],
            "approval_actions": ["Submit"],
            "error": str(e),
        }


@frappe.whitelist()
def approve(data):
    from frappe.utils.background_jobs import enqueue
    import json

    try:
        data = json.loads(data) if isinstance(data, str) else data

        if not data or not isinstance(data, list):
            return _("No valid data provided for approval")

        # Filter valid and approvable salary slip records
        valid_slips = []
        for item in data:
            if (
                isinstance(item, dict)
                and item.get("salary_slip_id")
                and item.get("salary_slip_id") != "Total"
            ):
                # Check if the salary slip can be approved using dynamic workflow info
                docstatus = item.get("docstatus")
                workflow_state = item.get("workflow_state")

                # Convert status display back to numeric if needed
                if isinstance(docstatus, str):
                    status_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
                    docstatus = status_map.get(docstatus, docstatus)

                # Get cached workflow info for validation
                workflow_info = get_cached_workflow_info()

                if is_approvable(docstatus, workflow_state, workflow_info):
                    valid_slips.append(item)

        if not valid_slips:
            return _("No valid salary slips found for approval")

        enqueue(
            method=enqueue_approve,
            queue="short",
            timeout=10000,
            job_name="approve_salary_slip",
            is_async=True,
            kwargs={"data": valid_slips},
        )
        return _("Processing {0} salary slip(s) for approval").format(len(valid_slips))

    except Exception as e:
        frappe.log_error(f"Error in approve function: {str(e)}")
        return _("Error occurred while processing approval request")


def enqueue_approve(kwargs):
    from frappe.model.workflow import apply_workflow

    data = kwargs.get("data", [])
    success_count = 0
    error_count = 0
    skipped_count = 0
    errors = []
    success_slips = []

    # Get workflow info once for all processing
    workflow_info = get_cached_workflow_info()

    for item in data:
        if not item.get("salary_slip_id") or item.get("salary_slip_id") == "Total":
            continue

        salary_slip_id = item.get("salary_slip_id")
        employee_name = item.get("employee_name", "Unknown")

        try:
            doc = frappe.get_doc("Salary Slip", salary_slip_id)

            # Double-check if the slip can still be approved using dynamic workflow info
            if not is_approvable(
                doc.docstatus, getattr(doc, "workflow_state", None), workflow_info
            ):
                errors.append(
                    f"Salary Slip {salary_slip_id} ({employee_name}): Cannot be approved in current state"
                )
                skipped_count += 1
                continue

            # Use dynamic workflow information
            if workflow_info.get("has_workflow"):
                # Use workflow if available - try dynamic approval actions
                approval_actions = workflow_info.get(
                    "approval_actions", ["Approve", "Submit", "Accept"]
                )
                action_applied = False

                for action in approval_actions:
                    try:
                        apply_workflow(doc, action)
                        success_count += 1
                        success_slips.append(f"{salary_slip_id} ({employee_name})")
                        action_applied = True
                        frappe.db.commit()
                        break
                    except Exception:
                        continue

                if not action_applied:
                    errors.append(
                        f"Salary Slip {salary_slip_id} ({employee_name}): No valid workflow action found from {approval_actions}"
                    )
                    error_count += 1
            else:
                # No workflow - simple submit if draft
                if doc.docstatus == 0:
                    doc.submit()
                    success_count += 1
                    success_slips.append(f"{salary_slip_id} ({employee_name})")
                    frappe.db.commit()
                else:
                    errors.append(
                        f"Salary Slip {salary_slip_id} ({employee_name}): Already submitted or cancelled"
                    )
                    error_count += 1

        except Exception as e:
            error_msg = f"Salary Slip {salary_slip_id} ({employee_name}): {str(e)}"
            errors.append(error_msg)
            frappe.log_error(f"Error approving salary slip {salary_slip_id}: {str(e)}")
            error_count += 1
            continue

    # Create detailed summary message
    summary_parts = []
    if success_count > 0:
        summary_parts.append(f"✅ {success_count} salary slip(s) approved successfully")
    if error_count > 0:
        summary_parts.append(f"❌ {error_count} failed")
    if skipped_count > 0:
        summary_parts.append(f"⏭️ {skipped_count} skipped")

    summary_msg = "Approval Process Completed:\n" + "\n".join(summary_parts)

    # Add details of successful approvals
    if success_slips:
        summary_msg += f"\n\nSuccessfully approved:\n• " + "\n• ".join(
            success_slips[:5]
        )
        if len(success_slips) > 5:
            summary_msg += f"\n• ... and {len(success_slips) - 5} more"

    # Log detailed errors if any
    if errors:
        error_log = "\n".join(errors)
        frappe.log_error(error_log, "Salary Slip Approval Errors")
        if len(errors) <= 3:
            summary_msg += f"\n\nErrors:\n• " + "\n• ".join(errors)
        else:
            summary_msg += f"\n\nErrors: {len(errors)} errors occurred. Check Error Log for details."

    # Send notification to user
    frappe.publish_realtime("msgprint", summary_msg, user=frappe.session.user)
