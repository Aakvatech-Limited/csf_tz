// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Import Exchange Differences"] = {
    "filters": [
        {
            "fieldname": "company",
            "fieldtype": "Link",
            "label": __("Company"),
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "fieldtype": "Date",
            "label": __("From Date"),
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "fieldtype": "Date",
            "label": __("To Date"),
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "purchase_invoice",
            "fieldtype": "Link",
            "label": __("Purchase Invoice"),
            "options": "Purchase Invoice"
        },
        {
            "fieldname": "supplier",
            "fieldtype": "Link",
            "label": __("Supplier"),
            "options": "Supplier"
        },
        {
            "fieldname": "currency",
            "fieldtype": "Link",
            "label": __("Currency"),
            "options": "Currency"
        },
        {
            "fieldname": "status",
            "fieldtype": "Select",
            "label": __("Status"),
            "options": "\nDraft\nActive\nCompleted\nCancelled"
        }
    ]
};
