// Copyright (c) 2016, Aakvatech and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Salary Register csf"] = {
  onload: function (report) {
    // Initialize workflow info
    report.workflow_info = null;

    // Fetch workflow information first
    frappe.call({
      method: "csf_tz.csf_tz.report.salary_register_csf.salary_register_csf.get_workflow_info",
      callback: function(r) {
        if (r.message) {
          report.workflow_info = r.message;
          setup_approval_buttons(report);
        }
      }
    });
  },

  get_datatable_options(options) {
    return Object.assign(options, {
      checkboxColumn: true,
      events: {
        onCheckRow: function() {
          // Handle row selection - could add custom logic here if needed
        }
      }
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

// Setup approval buttons after workflow info is loaded
function setup_approval_buttons(report) {
  // Add Approve Selected button
  report.page.add_inner_button(__("Approve Selected"), function () {
    approve_selected_salary_slips(report);
  }, __("Approve"));

  // Add Approve All Approvable button
  report.page.add_inner_button(__("Approve All Approvable"), function () {
    approve_all_approvable_salary_slips(report);
  }, __("Approve"));
}

// Helper function to check if a salary slip can be approved using dynamic workflow info
function is_approvable(row, workflow_info) {
  if (!row.salary_slip_id || row.salary_slip_id === "Total") {
    return false;
  }

  // If no workflow info available, default to draft check
  if (!workflow_info) {
    return row.docstatus === "Draft" || row.docstatus === 0;
  }

  // If no workflow configured, only draft documents can be approved
  if (!workflow_info.has_workflow) {
    return row.docstatus === "Draft" || row.docstatus === 0;
  }

  // Check if current workflow state is in approvable states
  const approvable_states = workflow_info.approvable_states || [];

  if (row.workflow_state && approvable_states.includes(row.workflow_state)) {
    return true;
  }

  // If no workflow state but document is draft, it might be approvable
  if (!row.workflow_state && (row.docstatus === "Draft" || row.docstatus === 0)) {
    return true;
  }

  return false;
}

// Function to approve selected salary slips
function approve_selected_salary_slips(report) {
  if (!report.datatable || !report.datatable.rowmanager) {
    frappe.msgprint(__("Please wait for the report to load completely"));
    return;
  }

  let selected_rows = report.datatable.rowmanager.getCheckedRows();
  if (selected_rows.length === 0) {
    frappe.msgprint(__("Please select salary slips to approve"));
    return;
  }

  // Filter selected rows to only include approvable ones using dynamic workflow info
  let approvable_slips = selected_rows
    .map(row_index => report.data[row_index])
    .filter(row => is_approvable(row, report.workflow_info));

  if (approvable_slips.length === 0) {
    let workflow_msg = report.workflow_info && report.workflow_info.has_workflow ?
      `approvable states: ${report.workflow_info.approvable_states.join(', ')}` :
      "draft status";
    frappe.msgprint(__("No approvable salary slips selected. Only slips with {0} can be approved.", [workflow_msg]));
    return;
  }

  let skipped_count = selected_rows.length - approvable_slips.length;
  let message = __("Are you sure you want to approve {0} salary slip(s)?", [approvable_slips.length]);

  if (skipped_count > 0) {
    message += __("<br><small>Note: {0} selected slip(s) will be skipped as they cannot be approved.</small>", [skipped_count]);
  }

  frappe.confirm(
    message,
    function() {
      process_approval(approvable_slips, report);
    }
  );
}

// Function to approve all approvable salary slips
function approve_all_approvable_salary_slips(report) {
  if (!report.data || report.data.length === 0) {
    frappe.msgprint(__("No data available to approve"));
    return;
  }

  // Filter only salary slips that can be approved using dynamic workflow info
  let approvable_slips = report.data.filter(row => is_approvable(row, report.workflow_info));

  if (approvable_slips.length === 0) {
    let workflow_msg = report.workflow_info && report.workflow_info.has_workflow ?
      `approvable states: ${report.workflow_info.approvable_states.join(', ')}` :
      "draft status";
    frappe.msgprint(__("No salary slips available for approval. Only slips with {0} can be approved.", [workflow_msg]));
    return;
  }

  let total_slips = report.data.filter(row => row.salary_slip_id && row.salary_slip_id !== "Total").length;
  let message = __("Are you sure you want to approve all {0} approvable salary slip(s)?", [approvable_slips.length]);

  if (approvable_slips.length < total_slips) {
    let skipped = total_slips - approvable_slips.length;
    message += __("<br><small>Note: {0} slip(s) will be skipped as they cannot be approved.</small>", [skipped]);
  }

  frappe.confirm(
    message,
    function() {
      process_approval(approvable_slips, report);
    }
  );
}

// Common function to process approval
function process_approval(salary_slips, report) {
  frappe.call({
    method: "csf_tz.csf_tz.report.salary_register_csf.salary_register_csf.approve",
    args: { data: JSON.stringify(salary_slips) },
    freeze: true,
    freeze_message: __("Processing salary slip approvals..."),
    callback: function (r) {
      if (r.message) {
        frappe.msgprint(r.message);
        // Refresh the report to show updated data
        setTimeout(() => {
          report.refresh();
        }, 2000);
      }
    },
    error: function(r) {
      frappe.msgprint(__("Error occurred while processing approvals"));
      console.error(r);
    }
  });
}
