import frappe
from frappe import _


@frappe.whitelist()
def make_payments_initiation(payroll_entry_name, currency, stanbic_setting_name=None):
	if currency and not stanbic_setting_name:
		company, cheque_number = frappe.get_cached_value(
			"Payroll Entry", payroll_entry_name, ["company", "cheque_number"]
		)
		if cheque_number:
			frappe.throw(
				_(
					f"Payments initiation {cheque_number} already created for payroll entry {payroll_entry_name}. Please remove the cheque number and try again if you really want to create the payments initiation file."
				),
				title="Payments initiation already created",
			)
		stanbic_setting_doc = frappe.get_doc("Stanbic Setting", {"company": company, "currency": currency})
		stanbic_setting_name = stanbic_setting_doc.name

	if not stanbic_setting_name:
		frappe.throw(
			f"Stanbic Setting not found for currency {currency}",
			title="Stanbic Setting not found",
		)

	payments_initiation_doc = frappe.new_doc("Stanbic Payments Initiation")
	payments_initiation_doc.payroll_entry = payroll_entry_name
	payments_initiation_doc.stanbic_setting = stanbic_setting_name
	payments_initiation_doc.set_data()
	frappe.msgprint(_(f"Payments Initiation {payments_initiation_doc.name} created successfully."))
	frappe.db.set_value(
		"Payroll Entry",
		payroll_entry_name,
		"cheque_date",
		payments_initiation_doc.posting_date,
	)
	frappe.db.set_value(
		"Payroll Entry",
		payroll_entry_name,
		"cheque_number",
		payments_initiation_doc.name,
	)
	return payments_initiation_doc
