// Copyright (c) 2016, Aakvatech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Salary Register csf"] = {
  onload: function (report) {
    report.page.add_inner_button(__("Approve"), function () {
      return frappe.call({
        method:
          "csf_tz.csf_tz.report.salary_register_csf.salary_register_csf.approve",
        args: { data: report.data },
        callback: function (r) {
          frappe.msgprint(__("Starting Approve Processing"));
          console.info(r.message);
        },
      });
    });
  },
  "filters": [
    {
      "fieldname": "company",
      "label": __("Company"),
      "fieldtype": "Link",
      "options": "Company",
      "default": frappe.defaults.get_user_default("Company"),
      "width": "100px",
      "reqd": 1
    },
    {
      "fieldname": "from_date",
      "label": __("From"),
      "fieldtype": "Date",
      "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      "reqd": 1,
      "width": "100px"
    },
    {
      "fieldname": "to_date",
      "label": __("To"),
      "fieldtype": "Date",
      "default": frappe.datetime.get_today(),
      "reqd": 1,
      "width": "100px"
    },
    {
      "fieldname": "currency",
      "fieldtype": "Link",
      "options": "Currency",
      "label": __("Currency"),
      "default": erpnext.get_currency(frappe.defaults.get_default("Company")),
      "width": "50px",
      "reqd": 1
    },
    {
      "fieldname": "employee",
      "label": __("Employee"),
      "fieldtype": "Link",
      "options": "Employee",
      "width": "100px"
    },
    {
      fieldname: "department",
      label: __("Department"),
      fieldtype: "Link",
      options: "Department",
      default: "",
      width: "100px",
      get_query: function () {
        var company = frappe.query_report.get_filter_value("company");
        return {
          doctype: "Department",
          filters: {
            company: company,
          },
        };
      },
    },
    {
      "fieldname": "docstatus",
      "label": __("Document Status"),
      "fieldtype": "Select",
      "options": ["Draft", "Submitted", "Cancelled"],
      "default": "Submitted",
      "width": "100px"
    },
    {
      "fieldname": "multi_currency",
      "label": __("Multi Currency"),
      "fieldtype": "Check",
    }
  ]
};
