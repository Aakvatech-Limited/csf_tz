from __future__ import unicode_literals

import frappe
from frappe import _

from csf_tz import console


@frappe.whitelist()
def get_landed_cost_expenses(import_file=None):
    if not import_file:
        return

    journal_entry = frappe.qb.DocType("Journal Entry")
    journal_entry_account = frappe.qb.DocType("Journal Entry Account")
    je_landed_cost = (
        frappe.qb.from_(journal_entry)
        .inner_join(journal_entry_account)
        .on(journal_entry_account.parent == journal_entry.name)
        .select(
            journal_entry_account.account.as_("expense_account"),
            journal_entry.title.as_("description"),
            journal_entry_account.debit.as_("amount"),
        )
        .where(journal_entry.import_file == import_file)
        .where(journal_entry.docstatus == 1)
        .where(journal_entry_account.debit > 0)
    ).run(as_dict=True)
    # frappe.db.sql("""update `tabSales Order Item` set delivered_qty = 0
    # 			where parent = %s""", so.name)
    purchase_invoice = frappe.qb.DocType("Purchase Invoice")
    purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")
    pinv_landed_cost = (
        frappe.qb.from_(purchase_invoice)
        .inner_join(purchase_invoice_item)
        .on(purchase_invoice_item.parent == purchase_invoice.name)
        .select(
            purchase_invoice_item.expense_account,
            purchase_invoice.title.as_("description"),
            purchase_invoice_item.base_net_amount.as_("amount"),
        )
        .where(purchase_invoice.import_file == import_file)
        .where(purchase_invoice.docstatus == 1)
    ).run(as_dict=True)
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
