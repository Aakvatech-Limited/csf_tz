# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate
from frappe import _

class ForeignImportTransaction(Document):
    def validate(self):
        self.validate_currency()
        self.calculate_totals()
        self.set_status()
    
    def on_submit(self):
        self.update_status("Active")
    
    def on_cancel(self):
        self.cancel_related_journal_entries()
        self.update_status("Cancelled")
    
    def validate_currency(self):
        """Validate that the purchase invoice is in foreign currency"""
        if not self.currency:
            frappe.throw("Currency is required")
        
        company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
        if self.currency == company_currency:
            frappe.throw(f"Foreign Import Transaction can only be created for foreign currency invoices. Company currency is {company_currency}")
    
    def calculate_totals(self):
        """Calculate total gains and losses"""
        total_gain = 0
        total_loss = 0
        
        for diff in self.exchange_differences:
            if diff.difference_type == "Gain":
                total_gain += flt(diff.amount)
            else:
                total_loss += flt(diff.amount)
        
        self.total_gain_loss = total_gain - total_loss
        self.net_difference = self.total_gain_loss
    
    def set_status(self):
        """Set status based on completion"""
        if self.docstatus == 0:
            self.status = "Draft"
        elif self.docstatus == 1:
            # Check if all payments are made
            invoice_amount = flt(self.invoice_amount_foreign)
            total_paid = sum([flt(p.payment_amount_foreign) for p in self.payments])
            
            if total_paid >= invoice_amount:
                self.status = "Completed"
            else:
                self.status = "Active"
        else:
            self.status = "Cancelled"
    
    def update_status(self, status):
        """Update status without triggering validations"""
        frappe.db.set_value(self.doctype, self.name, "status", status)
    
    def cancel_related_journal_entries(self):
        """Cancel all related journal entries"""
        for diff in self.exchange_differences:
            if diff.journal_entry:
                try:
                    je = frappe.get_doc("Journal Entry", diff.journal_entry)
                    if je.docstatus == 1:
                        je.cancel()
                except Exception as e:
                    frappe.log_error(f"Error cancelling Journal Entry {diff.journal_entry}: {str(e)}")
    
    def add_exchange_difference(self, reference_type, reference_name, difference_type, amount, posting_date, remarks, journal_entry=None):
        """Add exchange difference entry"""
        diff_row = self.append("exchange_differences", {})
        diff_row.reference_type = reference_type
        diff_row.reference_name = reference_name
        diff_row.difference_type = difference_type
        diff_row.amount = amount
        diff_row.posting_date = posting_date
        diff_row.remarks = remarks
        diff_row.journal_entry = journal_entry
        
        self.calculate_totals()
        self.save()
        
        return diff_row
    
    def add_payment_detail(self, payment_entry):
        """Add payment detail from Payment Entry"""
        payment_doc = frappe.get_doc("Payment Entry", payment_entry)
        
        payment_row = self.append("payments", {})
        payment_row.payment_entry = payment_entry
        payment_row.payment_date = payment_doc.posting_date
        payment_row.payment_amount_foreign = payment_doc.paid_amount
        payment_row.payment_amount_base = payment_doc.base_paid_amount
        payment_row.payment_exchange_rate = payment_doc.source_exchange_rate
        
        # Calculate exchange difference
        original_rate = flt(self.original_exchange_rate)
        payment_rate = flt(payment_doc.source_exchange_rate)
        paid_amount = flt(payment_doc.paid_amount)
        
        if original_rate != payment_rate:
            exchange_diff = paid_amount * (payment_rate - original_rate)
            payment_row.exchange_difference = exchange_diff
        
        self.save()
        return payment_row
    
    def add_lcv_detail(self, lcv_name):
        """Add LCV detail from Landed Cost Voucher"""
        lcv_doc = frappe.get_doc("Landed Cost Voucher", lcv_name)
        
        lcv_row = self.append("landed_cost_vouchers", {})
        lcv_row.landed_cost_voucher = lcv_name
        lcv_row.lcv_date = lcv_doc.posting_date
        lcv_row.lcv_amount_base = lcv_doc.total_taxes_and_charges
        lcv_row.exchange_rate_used = flt(lcv_doc.get("conversion_rate", 1))
        
        # Get allocated amount from LCV items
        allocated_amount = 0
        for item in lcv_doc.items:
            allocated_amount += flt(item.applicable_charges)
        lcv_row.allocated_to_items = allocated_amount
        
        self.save()
        return lcv_row

    @frappe.whitelist()
    def recalculate_differences(self):
        """Manually recalculate all exchange differences"""
        # Import here to avoid circular imports
        from csf_tz.csftz_hooks.exchange_calculations import recalculate_import_differences
        return recalculate_import_differences(self.name)
    
    @frappe.whitelist()
    def get_exchange_summary(self):
        """Get summary of exchange differences"""
        summary = {
            "total_gain": 0,
            "total_loss": 0,
            "payment_differences": 0,
            "lcv_differences": 0,
            "manual_entries": 0
        }
        
        for diff in self.exchange_differences:
            amount = flt(diff.amount)
            if diff.difference_type == "Gain":
                summary["total_gain"] += amount
            else:
                summary["total_loss"] += amount
            
            # Categorize by reference type
            if diff.reference_type == "Payment Entry":
                summary["payment_differences"] += amount
            elif diff.reference_type == "Landed Cost Voucher":
                summary["lcv_differences"] += amount
            else:
                summary["manual_entries"] += amount
        
        summary["net_difference"] = summary["total_gain"] - summary["total_loss"]
        
        return summary