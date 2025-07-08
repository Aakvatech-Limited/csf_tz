import frappe
from frappe.utils import flt
from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee
from contextlib import contextmanager


@contextmanager
def temporary_user(user):
    original_user = frappe.session.user
    frappe.session.user = user
    try:
        yield
    finally:
        frappe.session.user = original_user


def execute(doc, method):
    if doc.docstatus != 1:
        return

    if not doc.travel_request_ref:
        return

    try:
        if frappe.db.exists(
            "Payment Entry", {"reference_no": doc.name, "docstatus": ["!=", 2]}
        ):
            frappe.msgprint("Payment Entry already exists for this advance")
            return

        with temporary_user("Administrator"):
            payment_entry = create_payment_entry(doc)
        if payment_entry:
            doc.reload()

    except Exception as e:
        frappe.throw(f"Error during Employee Advance submission: {str(e)}")


def create_payment_entry(doc):
    try:
        payment_entry = get_payment_entry_for_employee("Employee Advance", doc.name)

        if payment_entry:
            payment_entry.reference_no = doc.name
            payment_entry.reference_date = frappe.utils.nowdate()

            # Bypass all validations and permissions
            payment_entry.flags.ignore_permissions = True
            payment_entry.flags.ignore_validate = True
            payment_entry.flags.ignore_mandatory = True
            payment_entry.flags.ignore_links = True
            payment_entry.flags.ignore_user_permissions = True

            payment_entry.insert(ignore_permissions=True)
            frappe.msgprint(f"Payment Entry {payment_entry.name} created successfully")

            return payment_entry

    except Exception as e:
        frappe.throw(f"Error creating Payment Entry: {str(e)}")
