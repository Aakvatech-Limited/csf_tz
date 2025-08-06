// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Account Balance"] = {
    "filters": [
        {
            "fieldname": "account",
            "label": "Account(s)",
            "fieldtype": "MultiSelectList",
            "get_data": function(txt) {
                return frappe.db.get_link_options('Account', txt, {
                    company: frappe.defaults.get_user_default("Company")
                });
            },
            "reqd": 0
        }
    ]
};
