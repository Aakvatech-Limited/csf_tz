# Copyright (c) 2024, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.party import get_party_account


class CSFTZBankCharges(Document):
    def validate(self):
        self.total_bank_charges = sum(
            row.debit_amount
            for row in self.get("csf_tz_bank_charges_detail")
            if row.debit_amount > 0
        )

    def on_submit(self):
        self.payments = []
        for detail in self.get("csf_tz_bank_charges_detail"):
            pe_details = self.create_pe(
                detail.debit_amount, detail.value_date, detail.reference_number
            )

            detail.ref_docname = pe_details["reference_name"]
            detail.ref_doctype = pe_details["reference_type"]
            self.payments.append(pe_details)

        pi = frappe.new_doc("Purchase Invoice")
        pi.posting_date = self.posting_date
        pi.supplier = self.bank_supplier
        pi.exchange_rate = self.exchange_rate
        pi.currency = self.currency
        pi.company = self.company
        pi.append(
            "items",
            {
                "item_code": "Bank Charges",
                "qty": 1,
                "rate": self.total_bank_charges,
                "amount": self.total_bank_charges,
            },
        )

        try:
            pi.save(ignore_permissions=True)
            pi.submit()
            self.ref_pi = pi.name
            frappe.msgprint(f"PI {pi.name} created successfully")

            self.invoices = [
                {
                    "invoice_type": pi.doctype,
                    "invoice_number": pi.name,
                    "invoice_date": pi.posting_date,
                    "amount": pi.grand_total,
                    "outstanding_amount": pi.outstanding_amount,
                    "currency": pi.currency,
                    "exchange_rate": self.exchange_rate,
                }
            ]
            self.payment_reconcile()
        except Exception as e:
            frappe.throw(_("Error while creating Purchase Invoice: {0}").format(str(e)))

    def create_pe(self, debit_amount, value_date, reference_number):
        pe = frappe.new_doc("Payment Entry")
        pe.naming_series = "PE-"
        pe.posting_date = value_date
        pe.payment_type = "Pay"
        pe.party_type = "Supplier"
        pe.party = self.bank_supplier
        pe.company = self.company
        pe.paid_amount = debit_amount
        pe.received_amount = debit_amount
        pe.source_exchange_rate = self.exchange_rate
        pe.paid_from = self.account
        pe.paid_from_account_currency = self.currency
        pe.reference_date = value_date
        pe.reference_no = reference_number

        try:
            pe.save(ignore_permissions=True)
            pe.submit()
            frappe.msgprint(f"PE {pe.name} created successfully")
            return {
                "reference_type": pe.doctype,
                "reference_name": pe.name,
                "posting_date": pe.posting_date,
                "amount": pe.unallocated_amount,
                "unallocated_amount": pe.unallocated_amount,
                "difference_amount": 0,
                "currency": pe.paid_from_account_currency,
                "exchange_rate": self.exchange_rate,
            }
        except Exception as e:
            frappe.throw(_("Error while creating Payment Entry: {0}").format(str(e)))

    def payment_reconcile(self):
        try:
            reconcile = frappe.new_doc("Payment Reconciliation")
            reconcile.party_type = "Supplier"
            reconcile.party = self.bank_supplier
            reconcile.company = self.company
            reconcile.receivable_payable_account = get_party_account(
                "Supplier", self.bank_supplier, self.company
            )

            reconcile.invoices = []
            for invoice in self.invoices:
                invoice_entry = reconcile.append("invoices", {})
                invoice_entry.invoice_type = invoice["invoice_type"]
                invoice_entry.invoice_number = invoice["invoice_number"]
                invoice_entry.invoice_date = invoice["invoice_date"]
                invoice_entry.amount = invoice["amount"]
                invoice_entry.outstanding_amount = invoice["outstanding_amount"]
                invoice_entry.currency = invoice["currency"]
                invoice_entry.exchange_rate = invoice["exchange_rate"]

            reconcile.payments = []
            for payment in self.payments:
                payment_entry = reconcile.append("payments", {})
                payment_entry.reference_type = payment["reference_type"]
                payment_entry.reference_name = payment["reference_name"]
                payment_entry.posting_date = payment["posting_date"]
                payment_entry.amount = payment["amount"]
                payment_entry.unallocated_amount = payment["unallocated_amount"]
                payment_entry.difference_amount = payment["difference_amount"]
                payment_entry.currency = payment["currency"]
                payment_entry.exchange_rate = payment["exchange_rate"]

            reconcile.allocate_entries(
                {"invoices": self.invoices, "payments": self.payments}
            )

            reconcile.reconcile()
        except Exception as e:
            frappe.throw(
                _("An error occurred during payment reconciliation: {0}").format(str(e))
            )
