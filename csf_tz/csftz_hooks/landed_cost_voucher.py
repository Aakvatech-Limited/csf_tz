from __future__ import unicode_literals
import frappe
from frappe import _
import frappe
import os
from frappe.utils.background_jobs import enqueue
from frappe.utils.pdf import get_pdf, cleanup
from PyPDF2 import PdfFileWriter
from csf_tz import console


@frappe.whitelist()
def get_landed_cost_expenses(import_file=None):
    if not import_file:
        return

    je_landed_cost = frappe.db.sql("""SELECT jea.account as 'expense_account', je.title as 'description', jea.debit as 'amount'
                     FROM `tabJournal Entry` je
                     INNER JOIN `tabJournal Entry Account` jea
                         ON jea.parent = je.name
                     WHERE je.import_file = %s
                       AND je.docstatus = 1
                       AND jea.debit > 0""", import_file, as_dict=1)
    # frappe.db.sql("""update `tabSales Order Item` set delivered_qty = 0
    # 			where parent = %s""", so.name)
    pinv_landed_cost = frappe.db.sql("""SELECT pii.expense_account as 'expense_account', pi.title as 'description', pii.base_net_amount as 'amount'
                     FROM `tabPurchase Invoice` pi
                     INNER JOIN `tabPurchase Invoice Item` pii
                         ON pii.parent = pi.name
                     WHERE pi.import_file = %s
                       AND pi.docstatus = 1;""", import_file, as_dict=1)
    return je_landed_cost + pinv_landed_cost

def total_amount(doc, method):
    for item in doc.items:  
        if item.amount and item.applicable_charges:
            item.custom_total_amount = item.amount + item.applicable_charges
        else:
            item.custom_total_amount = 0
            
    if doc.items:
        grand_total = 0
        for item in doc.items:
            grand_total += item.custom_total_amount or 0
        doc.custom_grand_total = grand_total
    else:
        doc.custom_grand_total = 0