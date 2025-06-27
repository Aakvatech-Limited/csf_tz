frappe.ui.form.on("Salary Slip", {
    setup: function(frm) {
        if (frm.doc.has_payroll_approval == 1) {
            $('[data-label="Submit"]').parent().hide();
            $('[data-label="Approve"]').parent().hide();
            $('[data-label="Reject"]').parent().hide();
            $('[data-label="Cancel"]').parent().hide();
        }
        
    },
    refresh:function(frm) {
        if (frm.doc.has_payroll_approval == 1) {
            $('[data-label="Submit"]').parent().hide();
            $('[data-label="Approve"]').parent().hide();
            $('[data-label="Reject"]').parent().hide();
            $('[data-label="Cancel"]').parent().hide();

            if (frm.doc.workflow_state == "Open") {
                frm.trigger("create_update_slip_btn");
            } else if (frm.doc.workflow_state == "Ongoing Approval") {
                frm.clear_custom_buttons();
                frm.set_intro("");
                frm.disable_form();
                frm.set_intro(__("This Salary Slip is awaiting approval."));
            }

        } else {
            frm.trigger("create_update_slip_btn");
        }
    },

    onload: (frm) => {
        if (frm.doc.workflow_state == "Open") {
            frm.trigger("create_update_slip_btn");
        } else if (frm.doc.has_payroll_approval == 1) {
            $('[data-label="Submit"]').parent().hide();
            $('[data-label="Approve"]').parent().hide();
            $('[data-label="Reject"]').parent().hide();
            $('[data-label="Cancel"]').parent().hide();

            if (frm.doc.workflow_state == "Ongoing Approval") {
                frm.clear_custom_buttons();
                frm.set_intro("");
                frm.disable_form();
                frm.set_intro(__("This Salary Slip is awaiting approval."));
            }
        } else {
            frm.trigger("create_update_slip_btn");
        }
    },
    
    create_update_slip_btn: function (frm) {
        if (frm.doc.docstatus != 0 || frm.is_new()) {
            return
        }
        frm.add_custom_button(__("Update Salary Slip"), function() {
            frappe.call({
                method: 'csf_tz.api.payroll.update_slip',
                args: {
                    salary_slip: frm.doc.name,
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                    }
                }
            });
        });
    },
});