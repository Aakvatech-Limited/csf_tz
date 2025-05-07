import frappe
from frappe.utils import flt
from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee

# from hrms.hr.doctype.expense_claim.expense_claim import get_expense_claim


def execute(doc, method):
    if doc.docstatus != 1:
        return

    if not doc.travel_request_ref:
        return

    try:
        payment_entry = create_payment_entry(doc)
        doc.reload()

    except Exception as e:
        frappe.throw(f"Error during Employee Advance submission: {str(e)}")


def create_payment_entry(doc):
    try:
        payment_entry = get_payment_entry_for_employee("Employee Advance", doc.name)

        if payment_entry:
            payment_entry.reference_no = doc.name
            payment_entry.reference_date = frappe.utils.nowdate()

            # payment_entry.submit()
            frappe.msgprint(f"Payment Entry {payment_entry.name} created successfully")

            return payment_entry

    except Exception as e:
        frappe.throw(f"Error creating Payment Entry: {str(e)}")
