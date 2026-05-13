import frappe


CUSTOM_FIELDS = (
    "Employee-overtime_components",
    "Employee-employee_ot_component",
    "Salary Slip-overtime_components",
    "Salary Slip-salary_slip_ot_component",
)


def execute():
    for field_name in CUSTOM_FIELDS:
        frappe.delete_doc_if_exists("Custom Field", field_name, force=True)
