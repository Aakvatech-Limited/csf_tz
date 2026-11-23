# Copyright (c) 2020, Aakvatech and contributors
# For license information, please see license.txt


import erpnext
import frappe

# from csf_tz.custom_api import get_linked_docs_info,cancle_linked_docs,cancel_doc,delete_doc,delete_linked_docs
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from frappe import _
from frappe.model.document import Document


class ExpenseRecord(Document):
	# def on_cancel(self):
	# 	linked_doc_list = get_linked_docs_info(self.doctype,self.name)
	# 	cancle_linked_docs(linked_doc_list)
	# 	if self.journal_entry:
	# 		cancel_doc("Journal Entry",self.journal_entry)

	# def on_trash(self):
	# 	linked_doc_list = get_linked_docs_info(self.doctype,self.name)
	# 	delete_linked_docs(linked_doc_list)
	# 	if self.journal_entry:
	# 		delete_doc("Journal Entry",self.journal_entry)

	def validate(self):
		pass

	def on_submit(self):
		if self.supplier:
			self.create_purchase_invoice()
		else:
			self.create_journal_entry()

	def create_purchase_invoice(self):
		company = frappe.get_value("Expense Type", self.expense_type, "company")
		items = [
			{
				"item_code": self.item,
				"rate": self.amount,
				"qty": 1,
				"description": self.name + " - " + self.expense_type,
			}
		]
		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": company,
				"currency": erpnext.get_company_currency(company),
				"cost_center": frappe.get_value("Section", self.section, "cost_center"),
				"supplier": self.supplier,
				"posting_date": self.date,
				"set_posting_time": 1,
				"bill_no": self.bill_no,
				"bill_date": self.date,
				"document_type": self.doctype,
				"disable_rounded_total": 0,
				"expense_record": self.name,
				"items": items,
				"is_paid": 1,
				"cash_bank_account": frappe.get_value("Section", self.section, "default_cash_account"),
				"taxes_and_charges": frappe.get_value(
					"Section", self.section, "purchase_taxes_and_charges_template"
				),
			}
		)
		frappe.flags.ignore_account_permission = True
		pi.set_missing_values()
		getTax(pi)
		pi.calculate_taxes_and_totals()
		pi.insert(ignore_permissions=True)
		pi.save()
		self.purchase_invoice = pi.name
		invoice_url = frappe.utils.get_url_to_form(pi.doctype, pi.name)
		si_msgprint = f"Purchase Invoice Created <a href='{invoice_url}'>{pi.name}</a>"
		frappe.msgprint(_(si_msgprint))
		return pi.name

	def create_journal_entry(self):
		account_details = make_account_row(
			debit_account=frappe.get_value("Expense Type", self.expense_type, "expense_account"),
			credit_account=frappe.get_value("Section", self.section, "default_cash_account"),
			amount=self.amount,
			cost_center=frappe.get_value("Section", self.section, "cost_center"),
		)
		company = frappe.get_value("Section", self.section, "company")
		user_remark = (
			self.name + " " + self.doctype + " was created at " + self.section + " for " + self.expense_type
		)
		jv_doc = frappe.get_doc(
			dict(
				doctype="Journal Entry",
				posting_date=self.date,
				accounts=account_details,
				bill_no=self.bill_no,
				company=company,
				expense_record=self.name,
				user_remark=user_remark,
			)
		)
		jv_doc.flags.ignore_permissions = True
		frappe.flags.ignore_account_permission = True
		jv_doc.save()
		self.journal_entry = jv_doc.name
		jv_url = frappe.utils.get_url_to_form(jv_doc.doctype, jv_doc.name)
		si_msgprint = f"Journal Entry Created <a href='{jv_url}'>{jv_doc.name}</a>"
		frappe.msgprint(_(si_msgprint))
		return jv_doc.name


def getTax(purchase_invoice):
	taxes = get_taxes_and_charges("Purchase Taxes and Charges Template", purchase_invoice.taxes_and_charges)
	for tax in taxes:
		purchase_invoice.append("taxes", tax)


def make_account_row(debit_account, credit_account, amount, cost_center):
	accounts = []
	debit_row = dict(account=debit_account, debit_in_account_currency=amount, cost_center=cost_center)
	accounts.append(debit_row)
	credit_row = dict(account=credit_account, credit_in_account_currency=amount, cost_center=cost_center)
	accounts.append(credit_row)
	return accounts
