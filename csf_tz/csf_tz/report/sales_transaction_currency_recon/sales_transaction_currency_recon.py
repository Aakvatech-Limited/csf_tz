import frappe
from frappe.query_builder import Case, Criterion
from frappe.query_builder.functions import IfNull
from frappe.utils import flt
from pypika.terms import Bracket, ValueWrapper


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)

    columns = get_columns(filters)
    rows = get_rows(filters)

    if filters.get("view") == "Grouped by Customer":
        rows = group_by_customer(rows)

    # Differences MUST ALWAYS be in company currency
    for r in rows:
        r["ordered_minus_received"] = flt(r.get("ordered_amount_company")) - flt(r.get("received_amount_company"))
        r["ordered_minus_billed"] = flt(r.get("ordered_amount_company")) - flt(r.get("billed_amount_company"))
        r["billed_minus_received"] = flt(r.get("billed_amount_company")) - flt(r.get("received_amount_company"))

    return columns, rows


def validate_filters(filters):
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are required.")

    if filters.from_date > filters.to_date:
        frappe.throw("From Date cannot be after To Date.")


def get_columns(filters):
    currency_fields = [
        {
            "label": "Ordered Amount (Txn)",
            "fieldname": "ordered_amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150,
        },
        {
            "label": "Ordered Amount (Company)",
            "fieldname": "ordered_amount_company",
            "fieldtype": "Currency",
            "options": "company_currency",
            "width": 170,
        },
        {
            "label": "Received Amount (Txn)",
            "fieldname": "received_amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150,
        },
        {
            "label": "Received Amount (Company)",
            "fieldname": "received_amount_company",
            "fieldtype": "Currency",
            "options": "company_currency",
            "width": 170,
        },
        {
            "label": "Billed Amount (Txn)",
            "fieldname": "billed_amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150,
        },
        {
            "label": "Billed Amount (Company)",
            "fieldname": "billed_amount_company",
            "fieldtype": "Currency",
            "options": "company_currency",
            "width": 170,
        },

        # IMPORTANT: Differences ALWAYS in company currency
        {
            "label": "Ordered - Received (Company)",
            "fieldname": "ordered_minus_received",
            "fieldtype": "Currency",
            "options": "company_currency",
            "width": 190,
        },
        {
            "label": "Ordered - Billed (Company)",
            "fieldname": "ordered_minus_billed",
            "fieldtype": "Currency",
            "options": "company_currency",
            "width": 190,
        },
        {
            "label": "Billed - Received (Company)",
            "fieldname": "billed_minus_received",
            "fieldtype": "Currency",
            "options": "company_currency",
            "width": 190,
        },
    ]

    return [
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": "Doc Type", "fieldname": "doc_type", "fieldtype": "Data", "width": 130},
        {"label": "Doc No", "fieldname": "doc_no", "fieldtype": "Dynamic Link", "options": "doc_type", "width": 180},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 90},
        {"label": "Company Currency", "fieldname": "company_currency", "fieldtype": "Link", "options": "Currency", "width": 120},
        {"label": "Exchange Rate", "fieldname": "exchange_rate", "fieldtype": "Float", "width": 110},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 220},
        *currency_fields,
    ]


def get_rows(filters):
    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    company_currency = frappe.get_cached_value("Company", company, "default_currency")

    rows = []

    # Sales Order lines + tax row(s)
    rows.extend(get_sales_order_rows(filters, company_currency))
    rows.extend(get_sales_order_tax_rows(filters, company_currency))

    # Sales Invoice lines + tax row(s)
    rows.extend(get_sales_invoice_rows(filters, company_currency))
    rows.extend(get_sales_invoice_tax_rows(filters, company_currency))

    # Payments
    rows.extend(get_payment_rows(filters, company_currency))

    rows.sort(key=lambda r: (r.get("posting_date") or "", r.get("doc_type") or "", r.get("doc_no") or ""))
    return rows


def get_sales_order_rows(filters, company_currency):
    sales_order = frappe.qb.DocType("Sales Order")
    sales_order_item = frappe.qb.DocType("Sales Order Item")

    query = (
        frappe.qb.from_(sales_order)
        .inner_join(sales_order_item)
        .on(sales_order_item.parent == sales_order.name)
        .select(
            sales_order.customer,
            ValueWrapper("Sales Order").as_("doc_type"),
            sales_order.name.as_("doc_no"),
            sales_order.status,
            sales_order.transaction_date.as_("posting_date"),
            sales_order.currency,
            ValueWrapper(company_currency).as_("company_currency"),
            sales_order.conversion_rate.as_("exchange_rate"),
            sales_order_item.item_code,
            sales_order_item.item_name,
            get_ordered_amount(sales_order, sales_order_item.net_amount).as_("ordered_amount"),
            get_ordered_amount(sales_order, sales_order_item.base_net_amount).as_("ordered_amount_company"),
            ValueWrapper(0).as_("received_amount"),
            ValueWrapper(0).as_("received_amount_company"),
            ValueWrapper(0).as_("billed_amount"),
            ValueWrapper(0).as_("billed_amount_company"),
        )
        .where(sales_order.docstatus == 1)
        .where(
            get_common_conditions(
                filters,
                date_field=sales_order.transaction_date,
                customer_field=sales_order.customer,
                company_field=sales_order.company,
            )
        )
    )
    return query.run(as_dict=True)


def get_sales_order_tax_rows(filters, company_currency):
    sales_order = frappe.qb.DocType("Sales Order")

    query = (
        frappe.qb.from_(sales_order)
        .select(
            sales_order.customer,
            ValueWrapper("Sales Order").as_("doc_type"),
            sales_order.name.as_("doc_no"),
            sales_order.status,
            sales_order.transaction_date.as_("posting_date"),
            sales_order.currency,
            ValueWrapper(company_currency).as_("company_currency"),
            sales_order.conversion_rate.as_("exchange_rate"),
            ValueWrapper(None).as_("item_code"),
            ValueWrapper("TOTAL TAXES AND CHARGES").as_("item_name"),
            get_ordered_amount(sales_order, sales_order.total_taxes_and_charges).as_("ordered_amount"),
            get_ordered_amount(sales_order, sales_order.base_total_taxes_and_charges).as_(
                "ordered_amount_company"
            ),
            ValueWrapper(0).as_("received_amount"),
            ValueWrapper(0).as_("received_amount_company"),
            ValueWrapper(0).as_("billed_amount"),
            ValueWrapper(0).as_("billed_amount_company"),
        )
        .where(sales_order.docstatus == 1)
        .where(IfNull(sales_order.total_taxes_and_charges, 0) != 0)
        .where(
            get_common_conditions(
                filters,
                date_field=sales_order.transaction_date,
                customer_field=sales_order.customer,
                company_field=sales_order.company,
            )
        )
    )
    return query.run(as_dict=True)


def get_ordered_amount(sales_order, amount):
    return (
        Case()
        .when(sales_order.status == "Closed", amount * Bracket(IfNull(sales_order.per_billed, 0) / 100))
        .else_(amount)
    )


def get_sales_invoice_rows(filters, company_currency):
    sales_invoice = frappe.qb.DocType("Sales Invoice")
    sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")

    query = (
        frappe.qb.from_(sales_invoice)
        .inner_join(sales_invoice_item)
        .on(sales_invoice_item.parent == sales_invoice.name)
        .select(
            sales_invoice.customer,
            ValueWrapper("Sales Invoice").as_("doc_type"),
            sales_invoice.name.as_("doc_no"),
            sales_invoice.status,
            sales_invoice.posting_date,
            sales_invoice.currency,
            ValueWrapper(company_currency).as_("company_currency"),
            sales_invoice.conversion_rate.as_("exchange_rate"),
            sales_invoice_item.item_code,
            sales_invoice_item.item_name,
            ValueWrapper(0).as_("ordered_amount"),
            ValueWrapper(0).as_("ordered_amount_company"),
            ValueWrapper(0).as_("received_amount"),
            ValueWrapper(0).as_("received_amount_company"),
            sales_invoice_item.net_amount.as_("billed_amount"),
            sales_invoice_item.base_net_amount.as_("billed_amount_company"),
        )
        .where(sales_invoice.docstatus == 1)
        .where(
            get_common_conditions(
                filters,
                date_field=sales_invoice.posting_date,
                customer_field=sales_invoice.customer,
                company_field=sales_invoice.company,
            )
        )
    )
    return query.run(as_dict=True)


def get_sales_invoice_tax_rows(filters, company_currency):
    """Adds tax row per Sales Invoice since payments clear debtors inclusive of tax."""
    sales_invoice = frappe.qb.DocType("Sales Invoice")

    query = (
        frappe.qb.from_(sales_invoice)
        .select(
            sales_invoice.customer,
            ValueWrapper("Sales Invoice").as_("doc_type"),
            sales_invoice.name.as_("doc_no"),
            sales_invoice.status,
            sales_invoice.posting_date,
            sales_invoice.currency,
            ValueWrapper(company_currency).as_("company_currency"),
            sales_invoice.conversion_rate.as_("exchange_rate"),
            ValueWrapper(None).as_("item_code"),
            ValueWrapper("TOTAL TAXES AND CHARGES").as_("item_name"),
            ValueWrapper(0).as_("ordered_amount"),
            ValueWrapper(0).as_("ordered_amount_company"),
            ValueWrapper(0).as_("received_amount"),
            ValueWrapper(0).as_("received_amount_company"),
            sales_invoice.total_taxes_and_charges.as_("billed_amount"),
            sales_invoice.base_total_taxes_and_charges.as_("billed_amount_company"),
        )
        .where(sales_invoice.docstatus == 1)
        .where(IfNull(sales_invoice.total_taxes_and_charges, 0) != 0)
        .where(
            get_common_conditions(
                filters,
                date_field=sales_invoice.posting_date,
                customer_field=sales_invoice.customer,
                company_field=sales_invoice.company,
            )
        )
    )
    return query.run(as_dict=True)


def get_payment_rows(filters, company_currency):
    payment_entry = frappe.qb.DocType("Payment Entry")
    payment_reference = frappe.qb.DocType("Payment Entry Reference")
    exchange_rate = IfNull(payment_entry.source_exchange_rate, 1)

    # IMPORTANT SIGN CHANGE:
    # - Receive -> positive
    # - Pay (refund) -> negative
    received_amount = (
        Case()
        .when(payment_entry.payment_type == "Receive", payment_reference.allocated_amount)
        .when(payment_entry.payment_type == "Pay", -payment_reference.allocated_amount)
        .else_(0)
    )
    received_amount_company = (
        Case()
        .when(payment_entry.payment_type == "Receive", payment_reference.allocated_amount * exchange_rate)
        .when(payment_entry.payment_type == "Pay", -payment_reference.allocated_amount * exchange_rate)
        .else_(0)
    )

    query = (
        frappe.qb.from_(payment_entry)
        .inner_join(payment_reference)
        .on(payment_reference.parent == payment_entry.name)
        .select(
            payment_entry.party.as_("customer"),
            ValueWrapper("Payment Entry").as_("doc_type"),
            payment_entry.name.as_("doc_no"),
            payment_entry.status.as_("status"),
            payment_entry.posting_date.as_("posting_date"),
            payment_entry.paid_from_account_currency.as_("currency"),
            ValueWrapper(company_currency).as_("company_currency"),
            payment_entry.source_exchange_rate.as_("exchange_rate"),
            ValueWrapper(None).as_("item_code"),
            ValueWrapper(None).as_("item_name"),
            ValueWrapper(0).as_("ordered_amount"),
            ValueWrapper(0).as_("ordered_amount_company"),
            received_amount.as_("received_amount"),
            received_amount_company.as_("received_amount_company"),
            ValueWrapper(0).as_("billed_amount"),
            ValueWrapper(0).as_("billed_amount_company"),
        )
        .where(payment_entry.docstatus == 1)
        .where(payment_entry.party_type == "Customer")
        .where(payment_reference.reference_doctype.isin(["Sales Invoice"]))
        .where(
            get_common_conditions(
                filters,
                date_field=payment_entry.posting_date,
                customer_field=payment_entry.party,
                company_field=payment_entry.company,
            )
        )
    )
    return query.run(as_dict=True)


def get_common_conditions(filters, date_field, customer_field, company_field):
    conditions = [date_field.between(filters.from_date, filters.to_date)]

    if filters.get("customer"):
        conditions.append(customer_field == filters.customer)

    if filters.get("company"):
        conditions.append(company_field == filters.company)

    return Criterion.all(conditions)


def group_by_customer(rows):
    grouped = {}

    for r in rows:
        key = (r.get("customer") or "")
        if key not in grouped:
            grouped[key] = {
                "customer": r.get("customer"),
                "doc_type": "Grouped",
                "doc_no": None,
                "posting_date": None,
                "currency": None,
                "company_currency": r.get("company_currency"),
                "exchange_rate": None,
                "item_code": None,
                "item_name": None,
                "ordered_amount": 0,
                "ordered_amount_company": 0,
                "received_amount": 0,
                "received_amount_company": 0,
                "billed_amount": 0,
                "billed_amount_company": 0,
            }

        g = grouped[key]
        g["ordered_amount"] += flt(r.get("ordered_amount"))
        g["ordered_amount_company"] += flt(r.get("ordered_amount_company"))
        g["received_amount"] += flt(r.get("received_amount"))
        g["received_amount_company"] += flt(r.get("received_amount_company"))
        g["billed_amount"] += flt(r.get("billed_amount"))
        g["billed_amount_company"] += flt(r.get("billed_amount_company"))

    return list(grouped.values())
