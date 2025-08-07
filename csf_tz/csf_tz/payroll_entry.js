frappe.ui.form.on("Payroll Entry", {
  setup: function(frm) {
      frm.trigger("control_action_buttons");
      
  },
  refresh:function(frm) {
      frm.trigger("control_action_buttons");

      frappe.call({
        method: 'csf_tz.csftz_hooks.payroll.get_amounts_summary',
        args: {
            payroll_entry: frm.doc.name
        },
        callback: function (r) {
            if (r.message) {
                const summary = r.message;
                const html = `
                    <div style="padding: 10px;">
                        <h4><b>Amounts Summary</b></h4>
                        <table class="table table-bordered">
                            <tr><td><b>Total Gross Pay</b></td><td>${frappe.format(summary.gross_pay, {fieldtype: 'Currency'})}</td></tr>
                            <tr><td><b>Total Net Pay</b></td><td>${frappe.format(summary.net_pay, {fieldtype: 'Currency'})}</td></tr>
                            <tr><td><b>SDL</b></td><td>${frappe.format(summary.sdl, {fieldtype: 'Currency'})}</td></tr>
                            <tr><td><b>PAYE</b></td><td>${frappe.format(summary.paye, {fieldtype: 'Currency'})}</td></tr>
                            <tr><td><b>NSSF</b></td><td>${frappe.format(summary.nssf, {fieldtype: 'Currency'})}</td></tr>
                            <tr><td><b>NHIF</b></td><td>${frappe.format(summary.nhif, {fieldtype: 'Currency'})}</td></tr>
                        </table>
                    </div>
                `;
                frm.fields_dict.custom_dashboard && frm.fields_dict.custom_dashboard.$wrapper.html(html);
            }
        }
    });
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
