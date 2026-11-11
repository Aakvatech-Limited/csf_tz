import frappe
from frappe import _
from frappe.query_builder.functions import Sum

@frappe.whitelist()
def get_customer_total_unpaid_amount(customer, company=None):
    if not customer:
        return 0
    gl_entry = frappe.qb.DocType("GL Entry")
    query = (
        frappe.qb.from_(gl_entry)
        .select(
            gl_entry.company,
            Sum(gl_entry.debit_in_account_currency) - Sum(gl_entry.credit_in_account_currency),
        )
        .where(gl_entry.party_type == "Customer")
        .where(gl_entry.party == customer)
        .where(gl_entry.is_cancelled == 0)
        .groupby(gl_entry.company)
    )
    if company:
        query = query.where(gl_entry.company == company)
    company_wise_total_unpaid = frappe._dict(query.run())
    total_unpaid = 0
    if company:
        total_unpaid = company_wise_total_unpaid.get(company, 0)
    else:
        total_unpaid = sum(company_wise_total_unpaid.values())

    total_unpaid = frappe.format_value(total_unpaid, "Float")

    frappe.msgprint(_("Total Unpaid Amount is {0}").format(total_unpaid))
    return total_unpaid