import frappe
from frappe import _

@frappe.whitelist()
def get_customer_total_unpaid_amount(customer, company=None):
    if not customer:
        return 0
    company_condition = ""
    if company:
        company_condition = " and company = '{0}'".format(company)
    company_wise_total_unpaid = frappe._dict(
        frappe.db.sql(
            """
        select company, sum(debit_in_account_currency) - sum(credit_in_account_currency)
        from `tabGL Entry`
        where party_type = %s and party=%s
        and is_cancelled = 0 {0}
        group by company""".format(company_condition),
            ("Customer", customer),
        )
    )
    total_unpaid = 0
    if company:
        total_unpaid = company_wise_total_unpaid.get(company, 0)
    else:
        total_unpaid = sum(company_wise_total_unpaid.values())

    total_unpaid = frappe.format_value(total_unpaid, "Float")

    frappe.msgprint(_("Total Unpaid Amount is {0}").format(total_unpaid))
    return total_unpaid