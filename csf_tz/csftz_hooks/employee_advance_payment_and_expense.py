import frappe
from frappe.utils import flt
from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee


def execute(doc, method):
    if doc.docstatus != 1:
        return

    if not doc.travel_request_ref:
        return

    # Store original user and switch to Administrator context
    original_user = frappe.session.user

    try:
        frappe.set_user("Administrator")
        payment_entry = create_payment_entry(doc)
        if payment_entry:
            doc.reload()

    except Exception as e:
        frappe.throw(f"Error during Employee Advance submission: {str(e)}")
    finally:
        # Always restore original user
        frappe.set_user(original_user)


def create_payment_entry(doc):
    try:
        # This now runs in Administrator context, bypassing the permission check
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

            # Save with ignore_permissions=True so employees can create payment entries
            payment_entry.insert(ignore_permissions=True)

            frappe.msgprint(f"Payment Entry {payment_entry.name} created successfully")

            return payment_entry

    except Exception as e:
        frappe.throw(f"Error creating Payment Entry: {str(e)}")
