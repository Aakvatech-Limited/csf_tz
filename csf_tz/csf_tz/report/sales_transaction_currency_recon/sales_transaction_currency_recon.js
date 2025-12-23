// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Transaction Currency Recon"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("Company"),
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.get_today(),
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
    },
    {
      fieldname: "view",
      label: __("View"),
      fieldtype: "Select",
      options: ["Detailed", "Grouped by Customer"],
      default: "Detailed",
      reqd: 1,
    },
  ],
};
