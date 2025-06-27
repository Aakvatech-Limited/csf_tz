from __future__ import unicode_literals 
import frappe
from frappe.model.document import Document
from frappe.utils import today
from frappe import _
from csf_tz.custom_api import print_out
# from frappe.utils import from frappe.utils import today, format_datetime, now, nowdate, getdate, get_url, get_host_name, format_datetime, now, nowdate, getdate, get_url, get_host_name


def make_student_applicant_fees(doc, method):
    if doc.docstatus != 1:
        return
    if doc.application_status != "Awaiting Registration Fees" or doc.student_applicant_fee:
        return
    fee_structure = frappe.get_doc("Fee Structure", doc.fee_structure)
    student_name = doc.first_name
    if doc.middle_name:
        student_name += " " + doc.middle_name
    if doc.last_name:
        student_name += " " + doc.last_name
    
    fee_doc =frappe.get_doc ({
        'doctype': 'Student Applicant Fees',
        'student': doc.name,
        'student_name': student_name,
        'fee_schedule': None,
        'company': fee_structure.company,
        'posting_date': today(),
        'due_date': today(),
        'program_enrollment': doc.program_enrollment,
        'program': fee_structure.program, 
        'student_batch': None, 
        'student_email': doc.student_email_id, 
        'student_category': fee_structure.student_category,
        'academic_term': fee_structure.academic_term,
        'academic_year': fee_structure.academic_year, 
        'currency': frappe.get_value("Company", fee_structure.company, "default_currency"), 
        'fee_structure': doc.fee_structure, 
        'grand_total': fee_structure.total_amount, 
        'receivable_account': fee_structure.receivable_account, 
        'income_account': fee_structure.income_account, 
        'cost_center': fee_structure.cost_center, 
    })

    fee_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    fee_doc.save()
    callback_token = fee_doc.callback_token
    doc.bank_reference = fee_doc.bank_reference or "None"
    doc.student_applicant_fee = fee_doc.name or "None"
    doc.db_update()
    fee_doc.reload()
    fee_doc.callback_token = callback_token
    fee_doc.bank_reference = doc.bank_reference
    fee_doc.db_update()
    fee_doc.submit()