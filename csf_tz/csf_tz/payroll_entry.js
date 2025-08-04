frappe.ui.form.on("Payroll Entry", {
  setup: function(frm) {
      frm.trigger("control_action_buttons");
      
  },
  refresh: function (frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Opening Salary Register'), function () {
                // Ask for confirmation
                frappe.confirm(__('Open the Salary Register report for this Payroll Entry?'), function () {
                    // Redirect with filter
                    const report_name = "Salary Register csf";
                    const payroll_entry = frm.doc.name;
                    const report_url = `/app/query-report/${encodeURIComponent(report_name)}?payroll_entry=${encodeURIComponent(payroll_entry)}`;
                    
                    window.open(report_url, "_blank");
                });
            }).addClass('btn-primary');
        }

        frm.trigger("control_action_buttons");
    },
  onload: (frm) => {
      frm.trigger("control_action_buttons");
  },
  workflow_state: (frm) => {
      if (frm.doc.has_payroll_approval == 1) {
          frm.refresh();
      }
  },
  create_update_slips_btn: function (frm) {
      if (frm.doc.docstatus != 1) {
          return
      }
      frm.add_custom_button(__("Update Salary Slips"), function() {
          frappe.call({
              method: 'csf_tz.csftz_hooks.payroll.update_slips',
              args: {
                  payroll_entry: frm.doc.name,
              },
              callback: function(r) {
                  if (r.message) {
                      console.log(r.message);
                  }
              }
          });
      });
  },
  create_print_btn: function (frm) {
      if (frm.doc.docstatus != 1) {
          return
      }
      frm.add_custom_button(__("Print Salary Slips"), function() {
          frappe.call({
              method: 'csf_tz.csftz_hooks.payroll.print_slips',
              args: {
                  payroll_entry: frm.doc.name,
              },
              // callback: function(r) {
              //     if (r.message) {
              //         frm.reload_doc();
              //     }
              // }
          });
      });
  },
  create_journal_entry_btn: function (frm) {
      if (frm.doc.docstatus != 1 || frm.doc.salary_slips_submitted == 1) {
          return;
      }
      frm.add_custom_button(__("Create Journal Entry"), function () {
          frappe.call({
              method: 'csf_tz.csftz_hooks.payroll.create_journal_entry',
              args: {
                  payroll_entry: frm.doc.name,
              },
              // callback: function(r) {
              //     if (r.message) {
              //         frm.reload_doc();
              //     }
              // }
          });
      });
  },

  control_action_buttons: (frm) => {
      if (frm.doc.docstatus == 1 && frm.doc.has_payroll_approval == 1) {
          if (frm.doc.workflow_state == "Salary Slips Created") {
              frm.trigger("create_update_slips_btn");
              $('[data-label="Submit%20Salary%20Slip"]').hide();
          } else if (
              frm.doc.workflow_state == "Approval Requested" ||
              frm.doc.workflow_state == "Change Requested" ||
              frm.doc.workflow_state.includes("Reviewed")
          ) {
              frm.clear_custom_buttons();
              frm.set_intro("");
              frm.set_intro(__("This Payroll Entry is under approval."));
          } else if (frm.doc.workflow_state.includes("Approved")) {
              frm.trigger("create_print_btn");
              frm.trigger("create_journal_entry_btn");
          }
      } else {
          frm.trigger("create_update_slips_btn");
          frm.trigger("create_print_btn");
          frm.trigger("create_journal_entry_btn");
      }
  },
});
