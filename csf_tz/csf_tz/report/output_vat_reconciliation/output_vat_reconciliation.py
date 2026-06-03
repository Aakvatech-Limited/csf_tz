# Copyright (c) 2013, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import fmt_money


def execute(filters=None):
	columns, data = get_columns(), []
	credit_note_label = {"details": "Credit Note - Sales Returns"}
	sales_label = {"details": "Sales - Sales Returns"}
	totals = {}
	generate_sales_returns(filters, data, totals, sales_label)
	data[0]["std_sales"] = fmt_money(float(totals["total_std_sales"]), 2, data[1]["invoice_currency"])
	data[0]["vat"] = fmt_money(float(totals["vat"]), 2, data[1]["invoice_currency"])
	data[0]["ex_amount"] = fmt_money(float(totals["ex_amount"]), 2, data[1]["invoice_currency"])
	data[0]["total"] = fmt_money(float(totals["total"]), 2, data[1]["invoice_currency"])
	generate_credit_note(data, totals, credit_note_label)

	data.append(
		{
			"details": "Sales as VAT Returns",
			"std_sales": fmt_money(float(totals["total_std_sales"]), 2, data[1]["invoice_currency"]),
			"vat": fmt_money(float(totals["vat"]), 2, data[1]["invoice_currency"]),
			"ex_amount": fmt_money(float(totals["ex_amount"]), 2, data[1]["invoice_currency"]),
			"total": fmt_money(float(totals["total"]), 2, data[1]["invoice_currency"]),
		}
	)
	return columns, data


def generate_credit_note(data, totals, credit_note_label):
	for i in range(1, len(data)):
		if data[i]["details"] != "Credit Note - Sales Returns":
			credit_notes = frappe.get_list(
				"Sales Invoice",
				filters={"is_return": 1, "return_against": "ACC-SINV-2019-07382", "docstatus": 1},
				fields=["*"],
			)
			print(credit_notes)
			for ii in credit_notes:
				if i == 1:
					data.append(credit_note_label)

				totals["total_std_sales"] = (
					totals["total_std_sales"] + float(ii.total)
					if "total_std_sales" in totals
					else float(ii.total)
				)
				totals["vat"] = (
					totals["vat"] + float(ii.total_taxes_and_charges)
					if "vat" in totals
					else float(ii.total_taxes_and_charges)
				)
				totals["ex_amount"] = (
					totals["ex_amount"] + float(ii.grand_total)
					if "ex_amount" in totals
					else float(ii.grand_total)
				)
				totals["total"] = (
					totals["total"] + float(ii.total + ii.total_taxes_and_charges + ii.grand_total)
					if "total" in totals
					else float(ii.total + ii.total_taxes_and_charges + ii.grand_total)
				)

				data.append(
					{
						"details": ii.name,
						"std_sales": fmt_money(float(ii.total), 2, data[i]["invoice_currency"]),
						"vat": fmt_money(float(ii.total_taxes_and_charges), 2, data[i]["invoice_currency"]),
						"ex_amount": fmt_money(ii.grand_total, 2, data[i]["invoice_currency"]),
						"total": fmt_money(
							float(ii.total + ii.total_taxes_and_charges + ii.grand_total),
							2,
							data[i]["invoice_currency"],
						),
					}
				)


def generate_sales_returns(filters, data, totals, sales_label):
	efd_z_report_invoices = frappe.get_list(
		"EFD Z Report Invoice", filters={"parent": filters.get("efd_report")}, fields=["*"]
	)
	for idx, i in enumerate(efd_z_report_invoices):
		sales_invoice = frappe.get_doc("Sales Invoice", i.invoice_number).__dict__
		if idx == 0:
			data.append(sales_label)
		totals["total_std_sales"] = (
			totals["total_std_sales"] + float(sales_invoice["total"])
			if "total_std_sales" in totals
			else float(sales_invoice["total"])
		)
		totals["vat"] = (
			totals["vat"] + float(sales_invoice["total_taxes_and_charges"])
			if "vat" in totals
			else float(sales_invoice["total_taxes_and_charges"])
		)
		totals["ex_amount"] = (
			totals["ex_amount"] + float(sales_invoice["grand_total"])
			if "ex_amount" in totals
			else float(sales_invoice["grand_total"])
		)
		totals["total"] = (
			totals["total"]
			+ float(
				sales_invoice["total"]
				+ sales_invoice["total_taxes_and_charges"]
				+ sales_invoice["grand_total"]
			)
			if "total" in totals
			else float(
				sales_invoice["total"]
				+ sales_invoice["total_taxes_and_charges"]
				+ sales_invoice["grand_total"]
			)
		)
		data.append(
			{
				"details": i.invoice_number,
				"std_sales": fmt_money(float(sales_invoice["total"]), 2, i.invoice_currency),
				"vat": fmt_money(float(sales_invoice["total_taxes_and_charges"]), 2, i.invoice_currency),
				"ex_amount": fmt_money(sales_invoice["grand_total"], 2, i.invoice_currency),
				"total": fmt_money(
					float(
						sales_invoice["total"]
						+ sales_invoice["total_taxes_and_charges"]
						+ sales_invoice["grand_total"]
					),
					2,
					i.invoice_currency,
				),
				"invoice_currency": i.invoice_currency,
			}
		)


def get_columns():
	columns = [
		{"label": _("Details"), "fieldname": "details", "fieldtype": "Data", "width": 200},
		{"label": _("STD Sales"), "fieldname": "std_sales", "fieldtype": "Data", "width": 170},
		{"label": _("VAT"), "fieldname": "vat", "fieldtype": "Data", "width": 170},
		{"label": _("EX Amount"), "fieldname": "ex_amount", "fieldtype": "Data", "width": 170},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Data", "width": 170},
	]

	return columns
