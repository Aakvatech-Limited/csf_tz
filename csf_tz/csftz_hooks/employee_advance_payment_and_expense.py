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

<<<<<<< HEAD
        if payment_entry:
            create_expense_claim(doc)

=======
>>>>>>> origin/version-14
    except Exception as e:
        frappe.throw(f"Error during Employee Advance submission: {str(e)}")


def create_payment_entry(doc):
    try:
        payment_entry = get_payment_entry_for_employee("Employee Advance", doc.name)

        if payment_entry:
            payment_entry.reference_no = doc.name
            payment_entry.reference_date = frappe.utils.nowdate()

<<<<<<< HEAD
            payment_entry.submit()
=======
            # payment_entry.submit()
>>>>>>> origin/version-14
            frappe.msgprint(f"Payment Entry {payment_entry.name} created successfully")

            return payment_entry

    except Exception as e:
        frappe.throw(f"Error creating Payment Entry: {str(e)}")
<<<<<<< HEAD


def create_expense_claim(doc):
    try:

        payable_account = frappe.get_cached_value(
            "Company", doc.company, "default_expense_claim_payable_account"
        )

        if not payable_account:
            frappe.throw(
                f"Expense claim payable account is not set for the company {doc.company}"
            )

        costings = []
        travel_request = frappe.get_doc("Travel Request", doc.travel_request_ref)
        company_abbr = frappe.get_cached_value("Company", doc.company, "abbr")
        cost_center = travel_request.cost_center or f"Main - {company_abbr}"
        costings = [
            {
                "expense_type": costing.expense_type,
                "amount": costing.total_amount,
                "sanctioned_amount": costing.total_amount,
                "cost_center": cost_center,
            }
            for costing in travel_request.costings
        ]

        if not costings:
            frappe.throw(
                "No expenses available for this claim. Please add costing details to the Travel Request."
            )

        expense_claim = frappe.get_doc(
            {
                "doctype": "Expense Claim",
                "employee": doc.employee,
                "employee_name": doc.employee_name,
                "posting_date": frappe.utils.nowdate(),
                "total_claimed_amount": doc.advance_amount,
                "company": doc.company,
                "payable_account": payable_account,
                "expenses": costings,
                "approval_status": "Approved",
                "advances": [
                    {
                        "employee_advance": doc.name,
                        "advance_paid": doc.advance_amount,
                        "advance_account": doc.advance_account,
                        "allocated_amount": doc.advance_amount,
                    }
                ],
            }
        )

        # Insert and submit the expense claim
        expense_claim.insert(ignore_permissions=True)
        # expense_claim.submit()
        doc.reload()

        frappe.msgprint(f"Expense Claim {expense_claim.name} created successfully.")

    except Exception as e:
        frappe.throw(f"Error creating Expense Claim: {str(e)}")
=======
>>>>>>> origin/version-14
