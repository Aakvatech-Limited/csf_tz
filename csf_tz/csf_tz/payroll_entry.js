frappe.ui.form.on("Payroll Entry", {
  setup: function(frm) {
      frm.trigger("control_action_buttons");

  },
  refresh:function(frm) {
      frm.trigger("control_action_buttons");

      frm.trigger("add_filed_returns_button");

      if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Opening Salary Register'), function () {
                // Redirect with filter
				const report_name = "Salary Register";

				let report_url = `/desk/query-report/${encodeURIComponent(report_name)}?from_date=${encodeURIComponent(frm.doc.start_date)}&to_date=${encodeURIComponent(frm.doc.end_date)}${frm.doc.company ? `&company=${encodeURIComponent(frm.doc.company)}` : ""}&payroll_entry=${encodeURIComponent(frm.doc.name)}`;

				window.open(report_url, "_blank");
            }).addClass('btn-primary');
        }

      // An unsaved Payroll Entry has no persisted salary slips to summarize.
      if (frm.is_new()) return;

      frappe.call({
        method: 'csf_tz.csftz_hooks.payroll.get_amounts_summary',
        args: {
            payroll_entry: frm.doc.name
        },
        callback: function (r) {
            if (r.message) {
                const summary = r.message;
                const rows = [];
                const formatCurrency = value => frappe.format(value || 0, { fieldtype: 'Currency' });
                const escapeHtml = value => {
                    const stringValue = value || '';
                    if (frappe.utils && typeof frappe.utils.escape_html === 'function') {
                        return frappe.utils.escape_html(stringValue);
                    }
                    const element = document.createElement('div');
                    element.textContent = stringValue;
                    return element.innerHTML;
                };

                rows.push(`<tr><td><b>Total Gross Pay</b></td><td>${formatCurrency(summary.gross_pay)}</td></tr>`);
                rows.push(`<tr><td><b>Total Net Pay</b></td><td>${formatCurrency(summary.net_pay)}</td></tr>`);

                if (Array.isArray(summary.components)) {
                    summary.components.forEach(item => {
                        const label = escapeHtml(item.label || item.component);
                        rows.push(`<tr><td><b>${label}</b></td><td>${formatCurrency(item.amount)}</td></tr>`);
                    });
                }

                const html = `
                    <div style="padding: 10px;">
                        <h4><b>Amounts Summary</b></h4>
                        <table class="table table-bordered">
                            ${rows.join('')}
                        </table>
                    </div>
                `;
                frm.fields_dict.custom_dashboard && frm.fields_dict.custom_dashboard.$wrapper.html(html);
            }
        }
    });
  },
  add_filed_returns_button(frm) {
      if (frm.doc.docstatus !== 1 || !frm.doc.salary_slips_submitted || !frm.has_perm("write")) {
          return;
      }

      frm.add_custom_button(__("Upload Filed Returns"), () => {
          if (frm.attachments.max_reached(true)) return;

          frappe.prompt(
              [{
                  fieldname: "return_type",
                  label: __("Return Type"),
                  fieldtype: "Select",
                  options: ["", "PAYE", "SDL", "WCF", "NSSF", "NHIF", "HESLB"],
                  reqd: 1,
              }],
              ({ return_type }) => {
                  new frappe.ui.FileUploader({
                      doctype: frm.doctype,
                      docname: frm.docname,
                      frm,
                      fieldname: return_type,
                      method: "csf_tz.csftz_hooks.payroll.upload_filed_return",
                      allow_multiple: true,
                      allow_toggle_private: false,
                      disable_file_browser: true,
                      allow_web_link: false,
                      allow_google_drive: false,
                      on_success: (file) => frm.attachments.attachment_uploaded(file),
                  });
              },
              __("Upload Filed Returns"),
              __("Choose Files")
          );
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
