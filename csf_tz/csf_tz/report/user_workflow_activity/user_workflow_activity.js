// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.query_reports["User Workflow Activity"] = {
    "filters": [
        {
            "fieldname": "user",
            "label": __("User"),
            "fieldtype": "Link",
            "options": "User"
        },
        {
            "fieldname": "workflow",
            "label": __("Workflow"),
            "fieldtype": "Link",
            "options": "Workflow"
        },
        {
            "fieldname": "reference_doctype",
            "label": __("Reference DocType"),
            "fieldtype": "Link",
            "options": "DocType"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 0
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 0
        }
    ]
};
