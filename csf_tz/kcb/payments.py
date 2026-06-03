# kcb/payments.py
# Helper methods to build KCB Payments Initiation documents from ERPNext sources.

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.utils.data import escape_html
from frappe.utils.pdf import get_pdf


def _get_bank_account_details(bank_account_name: str | None) -> dict:
	if not bank_account_name:
		return {}
	return (
		frappe.get_value(
			"Bank Account",
			bank_account_name,
			["bank_account_no", "kcb_beneficiary_clearing_code", "bank"],
			as_dict=True,
		)
		or {}
	)


def _require_kcb_enabled():
	settings = frappe.get_single("KCB Settings")
	if not settings.enabled:
		frappe.throw(_("KCB Settings is disabled. Enable it to generate payments."))


def _validate_single_value(values, label):
	unique_values = {v for v in values if v}
	if len(unique_values) > 1:
		frappe.throw(_("{0} must be the same for all entries.").format(label))
	return unique_values.pop() if unique_values else ""


def _attach_supplier_batch_summary_pdf(target_name: str, doc, pe_docs):
	rows_html = ""
	for pe in pe_docs:
		rows_html += (
			"<tr>"
			f"<td>{escape_html(pe.name)}</td>"
			f"<td>{escape_html(pe.party_name or pe.party or '')}</td>"
			f"<td>{escape_html(str(pe.paid_amount or 0))}</td>"
			f"<td>{escape_html(pe.paid_from_account_currency or '')}</td>"
			f"<td>{escape_html(pe.party_bank_account or '')}</td>"
			"</tr>"
		)

	html = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; font-size: 12px; }}
          h3 {{ margin-bottom: 8px; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border: 1px solid #444; padding: 6px; text-align: left; }}
          th {{ background: #f2f2f2; }}
          .meta {{ margin-bottom: 10px; }}
        </style>
      </head>
      <body>
        <h3>KCB Supplier Batch Supporting Summary</h3>
        <div class="meta">
          <div><strong>KCB Batch:</strong> {escape_html(target_name)}</div>
          <div><strong>Posting Date:</strong> {escape_html(str(doc.posting_date or ''))}</div>
          <div><strong>Debit Account:</strong> {escape_html(str(doc.debit_account or ''))}</div>
          <div><strong>Currency:</strong> {escape_html(str(doc.currency or ''))}</div>
          <div><strong>Total Amount:</strong> {escape_html(str(doc.total_amount or 0))}</div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Payment Entry</th>
              <th>Beneficiary</th>
              <th>Amount</th>
              <th>Currency</th>
              <th>Party Bank Account</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </body>
    </html>
    """

	pdf_content = get_pdf(html)
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"SUP-{target_name}-Supplier-Summary.pdf",
			"attached_to_doctype": "KCB Payments Initiation",
			"attached_to_name": target_name,
			"content": pdf_content,
			"folder": "Home",
		}
	).save(ignore_permissions=True)


def _attach_payroll_batch_summary_pdf(target_name: str, doc, payroll_entry_name: str, slips):
	rows_html = ""
	for slip in slips:
		rows_html += (
			"<tr>"
			f"<td>{escape_html(slip.get('name') or '')}</td>"
			f"<td>{escape_html(slip.get('employee') or '')}</td>"
			f"<td>{escape_html(slip.get('employee_name') or '')}</td>"
			f"<td>{escape_html(str(slip.get('net_pay') or 0))}</td>"
			f"<td>{escape_html(slip.get('currency') or '')}</td>"
			"</tr>"
		)

	html = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; font-size: 12px; }}
          h3 {{ margin-bottom: 8px; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border: 1px solid #444; padding: 6px; text-align: left; }}
          th {{ background: #f2f2f2; }}
          .meta {{ margin-bottom: 10px; }}
        </style>
      </head>
      <body>
        <h3>KCB Payroll Batch Supporting Summary</h3>
        <div class="meta">
          <div><strong>KCB Batch:</strong> {escape_html(target_name)}</div>
          <div><strong>Payroll Entry:</strong> {escape_html(payroll_entry_name)}</div>
          <div><strong>Posting Date:</strong> {escape_html(str(doc.posting_date or ''))}</div>
          <div><strong>Debit Account:</strong> {escape_html(str(doc.debit_account or ''))}</div>
          <div><strong>Currency:</strong> {escape_html(str(doc.currency or ''))}</div>
          <div><strong>Total Amount:</strong> {escape_html(str(doc.total_amount or 0))}</div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Salary Slip</th>
              <th>Employee</th>
              <th>Employee Name</th>
              <th>Net Pay</th>
              <th>Currency</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </body>
    </html>
    """

	pdf_content = get_pdf(html)
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"SUP-{target_name}-Payroll-Summary.pdf",
			"attached_to_doctype": "KCB Payments Initiation",
			"attached_to_name": target_name,
			"content": pdf_content,
			"folder": "Home",
		}
	).save(ignore_permissions=True)


@frappe.whitelist()
def make_kcb_payments_initiation_from_payment_entries(payment_entries: str):
	_require_kcb_enabled()
	settings = frappe.get_single("KCB Settings")
	if isinstance(payment_entries, str):
		payment_entries = frappe.parse_json(payment_entries)

	if not payment_entries:
		frappe.throw(_("Please select at least one Payment Entry."))

	existing = frappe.get_all(
		"KCB Payments Initiation Info",
		filters={
			"source_doctype": "Payment Entry",
			"source_name": ["in", payment_entries],
			"docstatus": ["!=", 2],
		},
		fields=["parent", "source_name"],
	)
	if existing:
		names = ", ".join(sorted({row.source_name for row in existing}))
		frappe.throw(_("KCB Payments Initiation already exists for: {0}").format(names))

	pe_docs = [frappe.get_doc("Payment Entry", name) for name in payment_entries]

	invalid = [pe.name for pe in pe_docs if pe.docstatus != 1 or pe.payment_type != "Pay"]
	if invalid:
		frappe.throw(
			_("Only submitted Pay type Payment Entries are allowed. Invalid: {0}").format(", ".join(invalid))
		)

	paid_from_currencies = [pe.paid_from_account_currency for pe in pe_docs]

	currency = _validate_single_value(paid_from_currencies, _("Currency"))
	company_bank_account = settings.default_bank_account
	if not company_bank_account:
		frappe.throw(_("Company bank account is missing. Configure Default Bank Account in KCB Settings."))

	debit_account_details = _get_bank_account_details(company_bank_account)
	debit_account_no = debit_account_details.get("bank_account_no")
	if not debit_account_no:
		frappe.throw(_("Company bank account number is missing."))

	missing_party_accounts = []
	missing_clearing_codes = []
	invalid_clearing_codes = []

	doc = frappe.new_doc("KCB Payments Initiation")
	doc.posting_date = nowdate()
	doc.payment_type = "Supplier"
	doc.debit_account = debit_account_no
	doc.currency = currency

	total_amount = 0
	for pe in pe_docs:
		party_bank_details = _get_bank_account_details(pe.party_bank_account)
		beneficiary_account = party_bank_details.get("bank_account_no")
		beneficiary_clearing_code = party_bank_details.get("kcb_beneficiary_clearing_code")

		if not beneficiary_account:
			missing_party_accounts.append(pe.name)
		if not beneficiary_clearing_code:
			missing_clearing_codes.append(pe.name)
		elif len(str(beneficiary_clearing_code).strip()) != 6:
			invalid_clearing_codes.append(pe.name)

		row = doc.append("kcb_payments_initiation_info", {})
		row.source_doctype = "Payment Entry"
		row.source_name = pe.name
		row.beneficiary_name = pe.party_name or pe.party
		row.amount = pe.paid_amount
		row.currency = currency
		row.beneficiary_account = beneficiary_account or ""
		row.beneficiary_clearing_code = beneficiary_clearing_code or ""
		# KCB transaction codes: 59 Supplier, 58 Salaries, 487 RTGS, 75 SWIFT, 79 EAPS
		row.transaction_code = "59"
		row.my_ref = pe.name
		row.beneficiary_ref = pe.name
		row.payment_purpose = "Supplier Payment"

		total_amount += pe.paid_amount or 0

	if missing_party_accounts:
		frappe.throw(
			_("Missing supplier bank account number for: {0}").format(", ".join(missing_party_accounts))
		)
	if missing_clearing_codes:
		frappe.throw(
			_("Missing beneficiary clearing code for: {0}").format(", ".join(missing_clearing_codes))
		)
	if invalid_clearing_codes:
		frappe.throw(
			_("Beneficiary clearing code must be 6 characters for: {0}").format(
				", ".join(invalid_clearing_codes)
			)
		)

	doc.total_amount = total_amount
	doc.insert(ignore_permissions=True)

	# Supporting docs for supplier batches: attach one custom summary PDF.
	_attach_supplier_batch_summary_pdf(doc.name, doc, pe_docs)

	return doc.name


@frappe.whitelist()
def make_kcb_payments_initiation_from_payroll_entry(payroll_entry_name: str):
	_require_kcb_enabled()
	settings = frappe.get_single("KCB Settings")
	payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry_name)

	existing = frappe.get_all(
		"KCB Payments Initiation Info",
		filters={
			"source_doctype": "Payroll Entry",
			"source_name": payroll_entry_name,
			"docstatus": ["!=", 2],
		},
		fields=["parent"],
	)
	if existing:
		names = ", ".join(sorted({row.parent for row in existing if row.parent}))
		frappe.throw(
			_("KCB Payments Initiation already exists for Payroll Entry {0}: {1}").format(
				payroll_entry_name, names or _("Existing draft/submitted document")
			)
		)

	all_slips = frappe.get_all(
		"Salary Slip",
		filters={"payroll_entry": payroll_entry_name},
		fields=["name", "docstatus"],
	)
	if not all_slips:
		frappe.throw(
			_("No Salary Slips found for Payroll Entry {0}. Create and submit Salary Slips first.").format(
				payroll_entry_name
			)
		)

	pending_slips = [slip.name for slip in all_slips if slip.docstatus != 1]
	if pending_slips:
		frappe.throw(
			_(
				"Cannot create KCB Payments Initiation for Payroll Entry {0}. Submit all Salary Slips first. Pending: {1}"
			).format(payroll_entry_name, ", ".join(pending_slips))
		)

	slips = frappe.get_all(
		"Salary Slip",
		filters={"payroll_entry": payroll_entry_name, "docstatus": 1},
		fields=["name", "employee", "employee_name", "currency", "net_pay"],
	)

	if not slips:
		frappe.throw(_("No submitted Salary Slips found for this Payroll Entry."))

	currencies = [slip.currency for slip in slips]
	currency = _validate_single_value(currencies, _("Currency"))

	company_bank_account = settings.default_bank_account
	if not company_bank_account:
		frappe.throw(_("Payroll Entry missing bank account. Configure Default Bank Account in KCB Settings."))
	debit_account_details = _get_bank_account_details(company_bank_account)
	debit_account_no = debit_account_details.get("bank_account_no")
	if not debit_account_no:
		frappe.throw(_("Company bank account number is missing."))

	missing_employee_accounts = []
	missing_clearing_codes = []
	invalid_clearing_codes = []

	doc = frappe.new_doc("KCB Payments Initiation")
	doc.posting_date = payroll_entry.posting_date or nowdate()
	doc.payment_type = "Salary"
	doc.debit_account = debit_account_no
	doc.currency = currency

	total_amount = 0
	for slip in slips:
		employee = frappe.get_doc("Employee", slip.employee)
		beneficiary_account = employee.bank_ac_no
		beneficiary_clearing_code = employee.kcb_beneficiary_clearing_code

		if not beneficiary_account:
			missing_employee_accounts.append(employee.name)
		if not beneficiary_clearing_code:
			missing_clearing_codes.append(employee.name)
		elif len(str(beneficiary_clearing_code).strip()) != 6:
			invalid_clearing_codes.append(employee.name)

		row = doc.append("kcb_payments_initiation_info", {})
		row.source_doctype = "Payroll Entry"
		row.source_name = payroll_entry_name
		row.beneficiary_name = slip.employee_name
		row.amount = slip.net_pay
		row.currency = currency
		row.beneficiary_account = beneficiary_account or ""
		row.beneficiary_clearing_code = beneficiary_clearing_code or ""
		# KCB transaction codes: 58 Salaries
		row.transaction_code = "58"
		row.my_ref = slip.name
		row.beneficiary_ref = slip.name
		row.payment_purpose = _("Salary")

		total_amount += slip.net_pay or 0

	if missing_employee_accounts:
		frappe.throw(
			_("Missing employee bank account number for: {0}").format(", ".join(missing_employee_accounts))
		)
	if missing_clearing_codes:
		frappe.throw(
			_("Missing employee beneficiary clearing code for: {0}").format(", ".join(missing_clearing_codes))
		)
	if invalid_clearing_codes:
		frappe.throw(
			_("Employee beneficiary clearing code must be 6 characters for: {0}").format(
				", ".join(invalid_clearing_codes)
			)
		)

	doc.total_amount = total_amount
	doc.insert(ignore_permissions=True)

	# Supporting docs for payroll batches: attach one custom summary PDF.
	_attach_payroll_batch_summary_pdf(doc.name, doc, payroll_entry_name, slips)

	return doc.name
