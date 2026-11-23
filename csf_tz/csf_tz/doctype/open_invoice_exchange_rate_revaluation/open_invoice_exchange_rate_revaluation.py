# Copyright (c) 2019, Aakvatech and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import flt


class OpenInvoiceExchangeRateRevaluation(Document):
	def on_submit(self):
		last_doc_details = getLastCreatedDocument(self.name, self.currency)
		if last_doc_details:
			reverse_je = makeReverseJE(self.revaluation_date, last_doc_details[0].journal_entry)
			frappe.db.set_value(self.doctype, last_doc_details[0].name, "reverse_journal_entry", reverse_je)
			frappe.msgprint("Reverse Journal Entry Created: " + str(reverse_je))
		je_item = makeJEItem(self)
		res = makeJournalEntry(self.revaluation_date, je_item)
		frappe.db.set_value(self.doctype, self.name, "journal_entry", res)
		url = frappe.utils.get_url_to_form("Journal Entry", res)
		frappe.msgprint(f"Journal Entry for Exchange Rate Revaluation Created at <a href='{url}'>{res}</a>")


def getLastDocument(_self):
	doc = frappe.get_all(
		"Open Invoice Exchange Rate Revaluation", filters={}, fields=["name"], limit_page_length=1
	)
	return doc[0].name


def makeJEItem(self):
	item_dict = []
	for row in self.inv_err_detail:
		first_row_je = getFirstRow(abs(row.invoice_gain_or_loss), row.invoice_type)
		item_dict.append(first_row_je)
		second_row_je = getSecondRow(abs(row.invoice_gain_or_loss), row.invoice_type, row.invoice_number)
		item_dict.append(second_row_je)
	return item_dict


def getFirstRow(invoice_gain_or_loss, invoice_type):
	item_json = {}
	item_json["account"] = frappe.db.get_value(
		"Company", frappe.defaults.get_global_default("company"), "unrealized_exchange_gain_loss_account"
	)
	if flt(invoice_gain_or_loss) > 0:
		if invoice_type == "Sales Invoice":
			item_json["credit_in_account_currency"] = invoice_gain_or_loss
		else:
			item_json["debit_in_account_currency"] = invoice_gain_or_loss
	else:
		if invoice_type == "Sales Invoice":
			item_json["debit_in_account_currency"] = invoice_gain_or_loss
		else:
			item_json["credit_in_account_currency"] = invoice_gain_or_loss
	return item_json


def getSecondRow(invoice_gain_or_loss, invoice_type, invoice_number):
	item_json = {}
	item_json["reference_type"] = invoice_type
	item_json["reference_name"] = invoice_number
	item_json["user_remark"] = (
		str(frappe.db.get_value(str(invoice_type), invoice_number, "currency"))
		+ "@"
		+ str(frappe.db.get_value(str(invoice_type), invoice_number, "conversion_rate"))
	)
	if invoice_type == "Sales Invoice":
		item_json["account"] = frappe.db.get_value(invoice_type, invoice_number, "debit_to")
		item_json["party_type"] = "Customer"
		item_json["party"] = frappe.db.get_value(invoice_type, invoice_number, "customer")
		if flt(invoice_gain_or_loss) > 0:
			item_json["debit_in_account_currency"] = invoice_gain_or_loss
		else:
			item_json["credit_in_account_currency"] = invoice_gain_or_loss

	else:
		item_json["account"] = frappe.db.get_value(invoice_type, invoice_number, "credit_to")
		item_json["party_type"] = "Supplier"
		item_json["party"] = frappe.db.get_value(invoice_type, invoice_number, "supplier")
		if flt(invoice_gain_or_loss) > 0:
			item_json["credit_in_account_currency"] = invoice_gain_or_loss
		else:
			item_json["debit_in_account_currency"] = invoice_gain_or_loss
	return item_json


@frappe.whitelist()
def makeJournalEntry(date, je_item):
	j_entry = frappe.get_doc(
		dict(
			doctype="Journal Entry",
			posting_date=date,
			company=frappe.db.get_single_value("Global Defaults", "default_company"),
			accounts=je_item,
			voucher_type="Exchange Rate Revaluation",
			multi_currency=1,
		)
	)
	j_entry.save()
	j_entry.submit()
	return j_entry.name


@frappe.whitelist()
def makeReverseJE(date, name):
	je_doc = frappe.get_doc("Journal Entry", name)
	je_dict = []
	for entry in je_doc.accounts:
		je_json = {}
		je_json["account"] = entry.account
		je_json["credit_in_account_currency"] = entry.debit_in_account_currency
		je_json["debit_in_account_currency"] = entry.credit_in_account_currency
		je_json["party_type"] = entry.party_type if entry.party_type is not None else ""
		je_json["party"] = entry.party if entry.party is not None else ""
		je_json["reference_type"] = entry.reference_type if entry.reference_type is not None else ""
		je_json["reference_name"] = entry.reference_name if entry.reference_name is not None else ""
		je_dict.append(je_json)
	return makeJournalEntry(date, je_dict)


@frappe.whitelist()
def getLastCreatedDocument(name, currency):
	return frappe.get_all(
		"Open Invoice Exchange Rate Revaluation",
		filters=[
			["Open Invoice Exchange Rate Revaluation", "name", "!=", name],
			["Open Invoice Exchange Rate Revaluation", "docstatus", "=", "1"],
			["Open Invoice Exchange Rate Revaluation", "currency", "=", str(currency)],
		],
		fields=["name", "journal_entry"],
		order_by="revaluation_date desc",
		limit_start=0,
		limit_page_length=1,
	)
