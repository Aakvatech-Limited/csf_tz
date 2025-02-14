import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

def validate_bank_charges_account(payment_entry, method):
    """Ensure the Default Bank Charges Account is set before submitting Payment Entry"""

    if payment_entry.bank_charges > 0:
        company = payment_entry.company
        bank_charges_account = frappe.db.get_value("Company", company, "default_bank_charges_account")

        if not bank_charges_account:
            frappe.throw("Default Bank Charges Account is not set in Company settings. Please set it before submitting.")

def create_bank_charges_journal(payment_entry, method):
    """Creates a journal entry if bank charges are greater than 0"""

    if payment_entry.bank_charges > 0:
        company = payment_entry.company
        bank_account = payment_entry.paid_from
        bank_charges_account = frappe.db.get_value("Company", company, "default_bank_charges_account")

        if not bank_charges_account:
            frappe.throw("Default Bank Charges Account is not set in Company settings. Please set it before submitting.")

        # Create Journal Entry
        journal_entry = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Bank Entry",
            "company": company,
            "posting_date": payment_entry.posting_date,
            "accounts": [
                {
                    "account": bank_charges_account,
                    "debit_in_account_currency": payment_entry.bank_charges,
                    "credit_in_account_currency": 0
                },
                {
                    "account": bank_account,
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": payment_entry.bank_charges
                }
            ],
            "user_remark": payment_entry.bank_charges_description or f"Bank charges for Payment Entry {payment_entry.name}",
            "reference_doctype": "Payment Entry",
            "reference_name": payment_entry.name,
            "cheque_no": payment_entry.name,  
            "cheque_date": nowdate() 
        })
        journal_entry.insert()
        journal_entry.submit()

        payment_entry.db_set("bank_charges_journal_entry", journal_entry.name)
