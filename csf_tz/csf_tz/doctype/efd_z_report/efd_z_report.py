# -*- coding: utf-8 -*-
# Copyright (c) 2019, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime
from frappe.utils import flt


class EFDZReport(Document):
    def validate(self):
        if not self.efd_z_report_invoices:
            frappe.throw(_("No Sales Invoie Found in the table"))

    def get_number_of_ticked(self):
        total_checked = 0
        for i in self.efd_z_report_invoices:
            if i.include:
                total_checked += 1
        return total_checked

    @frappe.whitelist()
    def get_sales_invoice(self):

        date = datetime.strptime(
            str(self.z_report_date_time), "%Y-%m-%d %H:%M:%S"
        ).date()
        time = datetime.strptime(
            str(self.z_report_date_time), "%Y-%m-%d %H:%M:%S"
        ).time()

        sales_invoice = frappe.qb.DocType("Sales Invoice")
        sales_invoices = (
            frappe.qb.from_(sales_invoice)
            .select("*")
            .where(
                (sales_invoice.docstatus == 1)
                & ((sales_invoice.efd_z_report == "") | sales_invoice.efd_z_report.isnull())
                & (sales_invoice.status != "Return")
                & (sales_invoice.posting_date <= str(date))
                & (
                    (sales_invoice.posting_date < str(date))
                    | ((sales_invoice.posting_date == str(date)) & (sales_invoice.posting_time < str(time)))
                )
                & (
                    (sales_invoice.electronic_fiscal_device == self.electronic_fiscal_device)
                    | sales_invoice.electronic_fiscal_device.isnull()
                    | (sales_invoice.electronic_fiscal_device == "")
                )
            )
        ).run(as_dict=True)

        if not sales_invoices:
            frappe.throw("No Sales Invoice Fetch")

        for i in sales_invoices:
            if i.base_total_taxes_and_charges == 0:
                amt_ex__sr = i.base_total
            else:
                if i.base_net_total != i.base_total:
                    amt_ex__sr = i.base_grand_total - (
                        i.base_net_total + i.base_total_taxes_and_charges
                    )
                else:
                    amt_ex__sr = i.base_grand_total - (
                        (i.base_total_taxes_and_charges / 0.18)
                        + i.base_total_taxes_and_charges
                    )
            if amt_ex__sr < 0:
                amt_ex__sr = 0
            self.append(
                "efd_z_report_invoices",
                {
                    "invoice_number": i.name,
                    "invoice_date": i.posting_date,
                    "amt_excl_vat": flt(i.base_net_total, 2),
                    "vat": flt(i.base_total_taxes_and_charges, 2),
                    "amt_ex__sr": amt_ex__sr,
                    "invoice_amount": flt(i.base_rounded_total, 2),
                    "invoice_currency": i.currency,
                },
            )
        return True

    def before_submit(self):
        if abs(flt(self.total_turnover, 2) - flt(self.total_turnover_ticked, 2)) > (self.allowable_difference or 0):
            frappe.throw(_("Sales Invoice Amount {0} is not equal to Money Entered {1}".format(flt(self.total_turnover_ticked, 2), flt(self.total_turnover, 2))))
        if abs(flt(self.net_amount, 2) - flt(self.total_excluding_vat_ticked, 2)) > (self.allowable_difference or 0):
            frappe.throw(
                _("Total Excluding VAT {0} is not equal to Total Excluding VAT (Ticked) {1}".format(flt(self.net_amount, 2), flt(self.total_excluding_vat_ticked, 2)))
            )
        if abs(flt(self.total_vat, 2) - flt(self.total_vat_ticked, 2)) > (self.allowable_difference or 0):
            frappe.throw(_("Total VAT {0} is not equal to Total VAT (Ticked) {1}".format(flt(self.total_vat, 2), flt(self.total_vat_ticked, 2))))
        if abs(flt(self.total_turnover_ex_sr, 2) - flt(self.total_turnover_exempted__sp_relief_ticked, 2)) > (self.allowable_difference or 0):
            frappe.throw(
                _(
                    "Total Turnover Exempted / Sp. Relief {0} is not equal to Total Turnover Exempted / Sp. Relief (Ticked) {1}".format(
                        flt(self.total_turnover_ex_sr, 2), flt(self.total_turnover_exempted__sp_relief_ticked, 2)
                    )
                )
            )
        if self.get_number_of_ticked() != self.receipts_issued:
            frappe.throw(
                _(
                    "The Number of Sales Invoice (Include is checked) in the table is not equal to Receipts Issued"
                )
            )
        to_remove = []
        for invoice in self.efd_z_report_invoices:
            if not invoice.include:
                to_remove.append(invoice)
            else:
                invoice_doc = frappe.get_doc("Sales Invoice", invoice.invoice_number)
                if invoice_doc.efd_z_report:
                    frappe.throw(
                        _(
                            "The Sales Invoice {0} is linked to EFD Z Report {1}".format(
                                invoice.invoice_number, invoice_doc.efd_z_report
                            )
                        )
                    )
                else:
                    invoice_doc.efd_z_report = self.name
                    invoice_doc.flags.ignore_permissions = True
                    invoice_doc.save()
        [self.remove(invoice) for invoice in to_remove]

    def on_cancel(self):
        for invoice in self.efd_z_report_invoices:
            if invoice.include:
                invoice_doc = frappe.get_doc("Sales Invoice", invoice.invoice_number)
                if invoice_doc.efd_z_report:
                    invoice_doc.efd_z_report = ""
                    invoice_doc.flags.ignore_permissions = True
                    invoice_doc.save()
