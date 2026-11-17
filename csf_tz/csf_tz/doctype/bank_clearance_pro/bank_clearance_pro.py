# -*- coding: utf-8 -*-
# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, nowdate, fmt_money
from frappe import msgprint, _
from frappe.model.document import Document
from frappe.query_builder import Case, Order
from frappe.query_builder.functions import IfNull, Sum
from pypika.terms import ValueWrapper

form_grid_templates = {
    "journal_entries": "templates/form_grid/bank_reconciliation_grid.html"
}


class BankClearancePro(Document):
    @frappe.whitelist()
    def get_payment_entries(self):
        frappe.msgprint(_("Getting entries..."), alert=True)
        if not (self.from_date and self.to_date):
            frappe.throw(_("From Date and To Date are Mandatory"))

        if not self.account:
            frappe.throw(_("Account is mandatory to get payment entries"))

        journal_entries = self.get_journal_entries()
        payment_entries = self.get_bank_payment_entries()

        pos_sales_invoices, pos_purchase_invoices = [], []
        if self.include_pos_transactions:
            pos_sales_invoices = self.get_pos_sales_invoices()
            pos_purchase_invoices = self.get_pos_purchase_invoices()

        entries = sorted(list(payment_entries) + list(journal_entries + list(pos_sales_invoices) + list(pos_purchase_invoices)),
                        key=lambda k: k['posting_date'] or getdate(nowdate()))
        frappe.msgprint(_("Got " + str(len(entries)) + " entries."), alert=True)

        self.set('payment_entries', [])
        self.total_amount = 0.0

        for d in entries:
            row = self.append('payment_entries', {})

            amount = flt(d.get('debit', 0)) - flt(d.get('credit', 0))
            d.flt_amount = amount

            formatted_amount = fmt_money(abs(amount), 2, d.account_currency)
            d.amount = formatted_amount + " " + \
                (_("Dr") if amount > 0 else _("Cr"))

            d.pop("credit")
            d.pop("debit")
            d.pop("account_currency")
            row.update(d)
            self.total_amount += flt(amount)

    def get_journal_entries(self):
        journal_entry = frappe.qb.DocType("Journal Entry")
        journal_entry_account = frappe.qb.DocType("Journal Entry Account")
        conditions = (
            (journal_entry_account.account == self.account)
            & (journal_entry.docstatus == 1)
            & (journal_entry.posting_date >= self.from_date)
            & (journal_entry.posting_date <= self.to_date)
            & (IfNull(journal_entry.is_opening, "No") == "No")
        )
        if not self.include_reconciled_entries:
            conditions &= journal_entry.clearance_date.isnull() | (journal_entry.clearance_date == "0000-00-00")

        return (
            frappe.qb.from_(journal_entry)
            .join(journal_entry_account)
            .on(journal_entry_account.parent == journal_entry.name)
            .select(
                ValueWrapper("Journal Entry").as_("payment_document"),
                journal_entry.name.as_("payment_entry"),
                journal_entry.cheque_no.as_("cheque_number"),
                journal_entry.cheque_date,
                Sum(journal_entry_account.debit_in_account_currency).as_("debit"),
                Sum(journal_entry_account.credit_in_account_currency).as_("credit"),
                journal_entry.posting_date,
                journal_entry_account.against_account,
                journal_entry.clearance_date,
                journal_entry_account.account_currency,
            )
            .where(conditions)
            .groupby(journal_entry_account.account, journal_entry.name)
            .orderby(journal_entry.posting_date)
            .orderby(journal_entry.name, order=Order.desc)
        ).run(as_dict=True)

    def get_bank_payment_entries(self):
        payment_entry = frappe.qb.DocType("Payment Entry")
        is_paid_from_account = payment_entry.paid_from == self.account
        conditions = (
            (is_paid_from_account | (payment_entry.paid_to == self.account))
            & (payment_entry.docstatus == 1)
            & (payment_entry.posting_date >= self.from_date)
            & (payment_entry.posting_date <= self.to_date)
        )
        if not self.include_reconciled_entries:
            conditions &= payment_entry.clearance_date.isnull() | (payment_entry.clearance_date == "0000-00-00")
        if self.bank_account:
            conditions &= payment_entry.bank_account == self.bank_account

        return (
            frappe.qb.from_(payment_entry)
            .select(
                ValueWrapper("Payment Entry").as_("payment_document"),
                payment_entry.name.as_("payment_entry"),
                payment_entry.reference_no.as_("cheque_number"),
                payment_entry.reference_date.as_("cheque_date"),
                Case().when(is_paid_from_account, payment_entry.paid_amount).else_(0).as_("credit"),
                Case().when(is_paid_from_account, 0).else_(payment_entry.received_amount).as_("debit"),
                payment_entry.posting_date,
                IfNull(
                    payment_entry.party_name,
                    Case().when(is_paid_from_account, payment_entry.paid_to).else_(payment_entry.paid_from),
                ).as_("against_account"),
                payment_entry.clearance_date,
                Case()
                .when(payment_entry.paid_to == self.account, payment_entry.paid_to_account_currency)
                .else_(payment_entry.paid_from_account_currency)
                .as_("account_currency"),
            )
            .where(conditions)
            .orderby(payment_entry.posting_date)
            .orderby(payment_entry.name, order=Order.desc)
        ).run(as_dict=True)

    def get_pos_sales_invoices(self):
        sales_invoice = frappe.qb.DocType("Sales Invoice")
        sales_invoice_payment = frappe.qb.DocType("Sales Invoice Payment")
        account = frappe.qb.DocType("Account")
        return (
            frappe.qb.from_(sales_invoice_payment)
            .join(sales_invoice)
            .on(sales_invoice_payment.parent == sales_invoice.name)
            .join(account)
            .on(account.name == sales_invoice_payment.account)
            .select(
                ValueWrapper("Sales Invoice Payment").as_("payment_document"),
                sales_invoice_payment.name.as_("payment_entry"),
                sales_invoice_payment.amount.as_("debit"),
                sales_invoice.posting_date,
                sales_invoice.customer.as_("against_account"),
                sales_invoice_payment.clearance_date,
                account.account_currency,
                ValueWrapper(0).as_("credit"),
            )
            .where(
                (sales_invoice_payment.account == self.account)
                & (sales_invoice.docstatus == 1)
                & (sales_invoice.posting_date >= self.from_date)
                & (sales_invoice.posting_date <= self.to_date)
            )
            .orderby(sales_invoice.posting_date)
            .orderby(sales_invoice.name, order=Order.desc)
        ).run(as_dict=True)

    def get_pos_purchase_invoices(self):
        purchase_invoice = frappe.qb.DocType("Purchase Invoice")
        account = frappe.qb.DocType("Account")
        return (
            frappe.qb.from_(purchase_invoice)
            .join(account)
            .on(account.name == purchase_invoice.cash_bank_account)
            .select(
                ValueWrapper("Purchase Invoice").as_("payment_document"),
                purchase_invoice.name.as_("payment_entry"),
                purchase_invoice.paid_amount.as_("credit"),
                purchase_invoice.posting_date,
                purchase_invoice.supplier.as_("against_account"),
                purchase_invoice.clearance_date,
                account.account_currency,
                ValueWrapper(0).as_("debit"),
            )
            .where(
                (purchase_invoice.cash_bank_account == self.account)
                & (purchase_invoice.docstatus == 1)
                & (purchase_invoice.posting_date >= self.from_date)
                & (purchase_invoice.posting_date <= self.to_date)
            )
            .orderby(purchase_invoice.posting_date)
            .orderby(purchase_invoice.name, order=Order.desc)
        ).run(as_dict=True)

    def update_clearance_date(self):
        clearance_date_updated = False
        for d in self.get('payment_entries'):
            if d.clearance_date:
                if not d.payment_document:
                    frappe.throw(
                        _("Row #{0}: Payment document is required to complete the transaction"))

                if d.cheque_date and getdate(d.clearance_date) < getdate(d.cheque_date):
                    frappe.msgprint(_("Row #{0}: Clearance date {1} cannot be before Cheque Date {2}")
                                    .format(d.idx, d.clearance_date, d.cheque_date), alert=True)
                    frappe.throw(_("Row #{0}: Clearance date {1} cannot be before Cheque Date {2}")
                                .format(d.idx, d.clearance_date, d.cheque_date))

            if d.clearance_date or self.include_reconciled_entries:
                if not d.clearance_date:
                    d.clearance_date = None

                payment_entry = frappe.get_doc(
                    d.payment_document, d.payment_entry)
                payment_entry.db_set('clearance_date', d.clearance_date)

                clearance_date_updated = True

        if clearance_date_updated:
            self.get_payment_entries()
            msgprint(_("Clearance Date updated"))
        else:
            msgprint(_("Clearance Date not mentioned"))
