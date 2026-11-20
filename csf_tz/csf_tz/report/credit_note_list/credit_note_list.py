"""Credit Note List: submitted Sales Invoice returns and their original invoices."""

import frappe
from frappe.utils import add_days, add_months, get_first_day, get_last_day, getdate, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw("Company is required.")

    from_date, to_date = resolve_dates(filters)
    if getdate(from_date) > getdate(to_date):
        frappe.throw("From Date cannot be after To Date.")

    columns = get_columns()
    company_currency = frappe.get_cached_value("Company", filters.company, "default_currency")

    credit_filters = {
        "company": filters.company,
        "docstatus": 1,
        "is_return": 1,
        "posting_date": ["between", [from_date, to_date]],
    }
    if filters.get("customer"):
        credit_filters["customer"] = filters.customer
    if filters.get("credit_note"):
        credit_filters["name"] = filters.credit_note

    credit_notes = frappe.get_all(
        "Sales Invoice",
        filters=credit_filters,
        fields=[
            "name", "posting_date", "customer", "return_against",
            "base_net_total", "base_total_taxes_and_charges",
            "base_grand_total", "remarks",
        ],
        order_by="posting_date asc, name asc",
    )
    if not credit_notes:
        return columns, []

    reference_names = list({row.return_against for row in credit_notes if row.return_against})
    customer_names = list({row.customer for row in credit_notes if row.customer})

    references = {}
    if reference_names:
        for invoice in frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", reference_names], "company": filters.company},
            fields=[
                "name", "posting_date", "base_net_total",
                "base_total_taxes_and_charges", "base_grand_total",
            ],
        ):
            references[invoice.name] = invoice

    customers = {}
    if customer_names:
        for customer in frappe.get_all(
            "Customer",
            filters={"name": ["in", customer_names]},
            fields=["name", "tax_id"],
        ):
            customers[customer.name] = customer

    data = []
    for note in credit_notes:
        original = references.get(note.return_against)
        customer = customers.get(note.customer)
        data.append({
            "customer": note.customer,
            "tin": customer.tax_id if customer else "",
            "credit_note": note.name,
            "credit_note_date": note.posting_date,
            "credit_net": (note.base_net_total or 0) * -1,
            "credit_taxes": (note.base_total_taxes_and_charges or 0) * -1,
            "credit_total": (note.base_grand_total or 0) * -1,
            "original_invoice": note.return_against,
            "original_invoice_date": original.posting_date if original else None,
            "original_net": original.base_net_total if original else None,
            "original_taxes": original.base_total_taxes_and_charges if original else None,
            "original_total": original.base_grand_total if original else None,
            "currency": company_currency,
            "remarks": note.remarks or "",
        })

    return columns, data


def resolve_dates(filters):
    span = filters.get("time_span") or "This Month"
    current = getdate(today())
    if span == "Today":
        return current, current
    if span == "Yesterday":
        value = getdate(add_days(current, -1))
        return value, value
    if span == "This Week":
        start = getdate(add_days(current, -current.weekday()))
        return start, getdate(add_days(start, 6))
    if span == "Last Week":
        start = getdate(add_days(current, -current.weekday() - 7))
        return start, getdate(add_days(start, 6))
    if span == "This Month":
        return get_first_day(current), get_last_day(current)
    if span == "Last Month":
        previous = add_months(current, -1)
        return get_first_day(previous), get_last_day(previous)
    if span == "Period":
        if not filters.get("from_date") or not filters.get("to_date"):
            frappe.throw("From Date and To Date are required for Period.")
        return getdate(filters.from_date), getdate(filters.to_date)
    frappe.throw("Invalid Time Span.")


def get_columns():
    return [
        {"fieldname": "customer", "label": "Customer", "fieldtype": "Link", "options": "Customer", "width": 190},
        {"fieldname": "tin", "label": "TIN", "fieldtype": "Data", "width": 120},
        {"fieldname": "credit_note", "label": "Credit Note No", "fieldtype": "Link", "options": "Sales Invoice", "width": 175},
        {"fieldname": "credit_note_date", "label": "Credit Note Date", "fieldtype": "Date", "width": 115},
        {"fieldname": "credit_net", "label": "Credit Net (Base)", "fieldtype": "Currency", "options": "currency", "width": 135},
        {"fieldname": "credit_taxes", "label": "Credit Taxes & Charges (Base)", "fieldtype": "Currency", "options": "currency", "width": 170},
        {"fieldname": "credit_total", "label": "Credit Total (Base)", "fieldtype": "Currency", "options": "currency", "width": 135},
        {"fieldname": "original_invoice", "label": "Corresponding Invoice No", "fieldtype": "Link", "options": "Sales Invoice", "width": 180},
        {"fieldname": "original_invoice_date", "label": "Invoice Date", "fieldtype": "Date", "width": 110},
        {"fieldname": "original_net", "label": "Invoice Net (Base)", "fieldtype": "Currency", "options": "currency", "width": 140},
        {"fieldname": "original_taxes", "label": "Invoice Taxes & Charges (Base)", "fieldtype": "Currency", "options": "currency", "width": 170},
        {"fieldname": "original_total", "label": "Invoice Total (Base)", "fieldtype": "Currency", "options": "currency", "width": 140},
        {"fieldname": "remarks", "label": "Remarks", "fieldtype": "Small Text", "width": 250},
        {"fieldname": "currency", "label": "Currency", "fieldtype": "Link", "options": "Currency", "hidden": 1},
    ]
