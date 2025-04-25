frappe.ui.form.on('Employee Advance', {
    validate: function (frm) {
        checkAndValidateMaxUnclaimedEA(frm);
    }
});

function checkAndValidateMaxUnclaimedEA(frm) {
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'CSF TZ Settings',
            fieldname: ['track_unclaimed_employee_advances']
        },
        callback: function (settings_response) {
            if (settings_response && settings_response.message) {
                const trackUnclaimed = settings_response.message.track_unclaimed_employee_advances;

                if (trackUnclaimed == 1) {
                    checkUnclaimedEAAndMaxLimit(frm);
                }
            }
        }
    });
}

function checkUnclaimedEAAndMaxLimit(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Employee Advance',
            filters: {
                status: ['not in', ['Claimed', 'Cancelled']],
                employee: frm.doc.employee
            },
            fields: ['name']
        },
        callback: function (ea_response) {
            if (ea_response && ea_response.message) {
                let unclaimed_count = ea_response.message.length;

                frappe.call({
                    method: 'frappe.client.get_value',
                    args: {
                        doctype: 'Company',
                        fieldname: ['max_unclaimed_ea'],
                        filters: {
                            name: frm.doc.company
                        }
                    },
                    callback: function (company_response) {
                        if (company_response && company_response.message) {
                            let max_unclaimed_ea = company_response.message.max_unclaimed_ea;

                            if (unclaimed_count >= max_unclaimed_ea) {
                                frappe.msgprint(__('The maximum number of unclaimed Employee Advances has been reached. Cannot create a new Employee Advance.'));
                                frappe.validated = false;
                            }
                        }
                    }
                });
            }
        }
    });
}
