import frappe
from frappe.utils import nowdate
from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee


def execute(doc, method):
    """Main execution function"""
    if doc.docstatus != 1 or not doc.travel_request_ref:
        return

    if frappe.db.exists(
        "Payment Entry", {"reference_no": doc.name, "docstatus": ["!=", 2]}
    ):
        frappe.msgprint("Payment Entry already exists for this advance")
        return

    try:
        payment_entry = create_payment_entry(doc)
        if payment_entry:
            doc.reload()
    except Exception as e:
        frappe.throw(f"Error creating payment entry: {str(e)}")


def create_payment_entry(doc):
    """Create payment entry with permission bypass"""
    # Set permission bypass flags globally for this operation
    frappe.flags.ignore_account_permission = True
    frappe.flags.ignore_permissions = True

    payment_entry = get_payment_entry_for_employee("Employee Advance", doc.name)

    # Set reference details
    payment_entry.update(
        {
            "reference_no": doc.name,
            "reference_date": nowdate(),
        }
    )

    # Apply permission bypass flags
    payment_entry.flags.ignore_permissions = True
    payment_entry.flags.ignore_validate = True
    payment_entry.flags.ignore_mandatory = True
    payment_entry.insert(ignore_permissions=True)

    frappe.msgprint(f"Payment Entry {payment_entry.name} created successfully")
    return payment_entry
