import frappe

import csf_tz.custom_api as custom_api


def create_delivery_note_for_all_pending_sales_invoice(doc=None, method=None):
    """Create draft Delivery Notes only for companies where auto creation is enabled."""
    company_list = frappe.get_all(
        "Company",
        filters={"enabled_auto_create_delivery_notes": 1},
        pluck="name",
    )

    if not company_list:
        return

    enabled_companies = set(company_list)
    invoices = custom_api.get_list_pending_sales_invoice()

    for invoice_row in invoices:
        if invoice_row.company not in enabled_companies:
            continue

        invoice = frappe.get_doc("Sales Invoice", invoice_row.name)
        custom_api.create_delivery_note(invoice)


custom_api.create_delivery_note_for_all_pending_sales_invoice = (
    create_delivery_note_for_all_pending_sales_invoice
)
