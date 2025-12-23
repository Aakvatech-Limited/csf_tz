import frappe
from frappe.utils import flt


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
    conditions, values = get_common_conditions(
        filters,
        date_field="so.transaction_date",
        customer_field="so.customer",
        company_field="so.company",
    )

    q = f"""
        SELECT
            so.customer AS customer,
            'Sales Order' AS doc_type,
            so.name AS doc_no,
            so.status AS status,
            so.transaction_date AS posting_date,
            so.currency AS currency,
            %(company_currency)s AS company_currency,
            so.conversion_rate AS exchange_rate,
            soi.item_code AS item_code,
            soi.item_name AS item_name,

            -- Ordered Amount (Txn)
            CASE
                WHEN so.status = 'Closed'
                    THEN soi.net_amount * (IFNULL(so.per_billed, 0) / 100)
                ELSE soi.net_amount
            END AS ordered_amount,

            -- Ordered Amount (Company)
            CASE
                WHEN so.status = 'Closed'
                    THEN soi.base_net_amount * (IFNULL(so.per_billed, 0) / 100)
                ELSE soi.base_net_amount
            END AS ordered_amount_company,

            0 AS received_amount,
            0 AS received_amount_company,
            0 AS billed_amount,
            0 AS billed_amount_company

        FROM `tabSales Order` so
        INNER JOIN `tabSales Order Item` soi ON soi.parent = so.name
        WHERE so.docstatus = 1
          AND {conditions}
    """
    values["company_currency"] = company_currency
    return frappe.db.sql(q, values, as_dict=True)


def get_sales_order_tax_rows(filters, company_currency):
    conditions, values = get_common_conditions(
        filters,
        date_field="so.transaction_date",
        customer_field="so.customer",
        company_field="so.company",
    )

    q = f"""
        SELECT
            so.customer AS customer,
            'Sales Order' AS doc_type,
            so.name AS doc_no,
            so.status AS status,
            so.transaction_date AS posting_date,
            so.currency AS currency,
            %(company_currency)s AS company_currency,
            so.conversion_rate AS exchange_rate,
            NULL AS item_code,
            'TOTAL TAXES AND CHARGES' AS item_name,

            CASE
                WHEN so.status = 'Closed'
                    THEN so.total_taxes_and_charges * (IFNULL(so.per_billed, 0) / 100)
                ELSE so.total_taxes_and_charges
            END AS ordered_amount,

            CASE
                WHEN so.status = 'Closed'
                    THEN so.base_total_taxes_and_charges * (IFNULL(so.per_billed, 0) / 100)
                ELSE so.base_total_taxes_and_charges
            END AS ordered_amount_company,

            0 AS received_amount,
            0 AS received_amount_company,
            0 AS billed_amount,
            0 AS billed_amount_company

        FROM `tabSales Order` so
        WHERE so.docstatus = 1
          AND IFNULL(so.total_taxes_and_charges, 0) != 0
          AND {conditions}
    """
    values["company_currency"] = company_currency
    return frappe.db.sql(q, values, as_dict=True)


def get_sales_invoice_rows(filters, company_currency):
    conditions, values = get_common_conditions(
        filters,
        date_field="si.posting_date",
        customer_field="si.customer",
        company_field="si.company",
    )

    q = f"""
        SELECT
            si.customer AS customer,
            'Sales Invoice' AS doc_type,
            si.name AS doc_no,
            si.status AS status,
            si.posting_date AS posting_date,
            si.currency AS currency,
            %(company_currency)s AS company_currency,
            si.conversion_rate AS exchange_rate,
            sii.item_code AS item_code,
            sii.item_name AS item_name,
            0 AS ordered_amount,
            0 AS ordered_amount_company,
            0 AS received_amount,
            0 AS received_amount_company,
            sii.net_amount AS billed_amount,
            sii.base_net_amount AS billed_amount_company
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND {conditions}
    """
    values["company_currency"] = company_currency
    return frappe.db.sql(q, values, as_dict=True)


def get_sales_invoice_tax_rows(filters, company_currency):
    """Adds tax row per Sales Invoice since payments clear debtors inclusive of tax."""
    conditions, values = get_common_conditions(
        filters,
        date_field="si.posting_date",
        customer_field="si.customer",
        company_field="si.company",
    )

    q = f"""
        SELECT
            si.customer AS customer,
            'Sales Invoice' AS doc_type,
            si.name AS doc_no,
            si.status AS status,
            si.posting_date AS posting_date,
            si.currency AS currency,
            %(company_currency)s AS company_currency,
            si.conversion_rate AS exchange_rate,
            NULL AS item_code,
            'TOTAL TAXES AND CHARGES' AS item_name,
            0 AS ordered_amount,
            0 AS ordered_amount_company,
            0 AS received_amount,
            0 AS received_amount_company,
            si.total_taxes_and_charges AS billed_amount,
            si.base_total_taxes_and_charges AS billed_amount_company
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
          AND IFNULL(si.total_taxes_and_charges, 0) != 0
          AND {conditions}
    """
    values["company_currency"] = company_currency
    return frappe.db.sql(q, values, as_dict=True)


def get_payment_rows(filters, company_currency):
    conditions, values = get_common_conditions(
        filters,
        date_field="pe.posting_date",
        customer_field="pe.party",
        company_field="pe.company",
    )

    # IMPORTANT SIGN CHANGE:
    # - Receive -> positive
    # - Pay (refund) -> negative
    q = f"""
        SELECT
            pe.party AS customer,
            'Payment Entry' AS doc_type,
            pe.name AS doc_no,
            pe.status AS status,
            pe.posting_date AS posting_date,
            pe.paid_from_account_currency AS currency,
            %(company_currency)s AS company_currency,
            pe.source_exchange_rate AS exchange_rate,
            NULL AS item_code,
            NULL AS item_name,
            0 AS ordered_amount,
            0 AS ordered_amount_company,
            (
                CASE
                    WHEN pe.payment_type = 'Receive' THEN per.allocated_amount
                    WHEN pe.payment_type = 'Pay' THEN -per.allocated_amount
                    ELSE 0
                END
            ) AS received_amount,
            (
                CASE
                    WHEN pe.payment_type = 'Receive' THEN per.allocated_amount * IFNULL(pe.source_exchange_rate, 1)
                    WHEN pe.payment_type = 'Pay' THEN -per.allocated_amount * IFNULL(pe.source_exchange_rate, 1)
                    ELSE 0
                END
            ) AS received_amount_company,
            0 AS billed_amount,
            0 AS billed_amount_company
        FROM `tabPayment Entry` pe
        INNER JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
        WHERE pe.docstatus = 1
          AND pe.party_type = 'Customer'
          AND per.reference_doctype IN ('Sales Invoice')
          AND {conditions}
    """
    values["company_currency"] = company_currency
    return frappe.db.sql(q, values, as_dict=True)


def get_common_conditions(filters, date_field, customer_field, company_field):
    conditions = [f"{date_field} BETWEEN %(from_date)s AND %(to_date)s"]
    values = {
        "from_date": filters.from_date,
        "to_date": filters.to_date,
    }

    if filters.get("customer"):
        conditions.append(f"{customer_field} = %(customer)s")
        values["customer"] = filters.customer

    if filters.get("company"):
        conditions.append(f"{company_field} = %(company)s")
        values["company"] = filters.company

    return " AND ".join(conditions), values


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
