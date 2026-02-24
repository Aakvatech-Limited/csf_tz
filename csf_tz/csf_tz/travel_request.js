frappe.ui.form.on('Travel Request', {
    refresh: function (frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button('Create Employee Advance', function () {
                checkSettingsAndCreateEA(frm);
            });
        }

        calculateTotalTravelCost(frm);
    },
    validate: function (frm) {
        calculateTotalTravelCost(frm);
    }
});

function makeFrappeCall(method, args, successCallback, errorCallback = () => { }) {
    frappe.call({
        method: method,
        args: args,
        callback: function (response) {
            if (response && response.message) {
                successCallback(response.message);
            } else {
                frappe.msgprint(__('An error occurred during the request.'));
                errorCallback();
            }
        },
        error: function (error) {
            frappe.msgprint(__('Failed to process the request.'));
            console.error(error);
            errorCallback();
        }
    });
}

function checkSettingsAndCreateEA(frm) {
    makeFrappeCall(
        'frappe.client.get_value',
        {
            doctype: 'CSF TZ Settings',
            fieldname: ['track_unclaimed_employee_advances']
        },
        function (settings_response) {
            const trackUnclaimed = settings_response.track_unclaimed_employee_advances;
            if (trackUnclaimed != 0) {
                checkIfEAExists(frm);
            } else {
                frappe.msgprint(__('Please enable <b>Track Unclaimed Employee Advances</b> in the CSF TZ Settings.'));
            }
        }
    );
}

function checkIfEAExists(frm) {
    makeFrappeCall(
        'frappe.client.get_list',
        {
            doctype: 'Employee Advance',
            filters: {
                travel_request_ref: frm.doc.name,
                docstatus: ['<', 2]
            },
            fields: ['name']
        },
        function (ea_response) {
            if (ea_response.length > 0) {
                let advanceNames = ea_response.map(ea => ea.name).join(', ');
                frappe.msgprint(__('Employee Advances already exist for this Travel Request: {0}. Cannot create another.', [advanceNames]));
            } else {
                checkUnclaimedCountAndCreateEA(frm);
            }
        }
    );
}

function checkUnclaimedCountAndCreateEA(frm) {
    makeFrappeCall(
        'frappe.client.get_list',
        {
            doctype: 'Employee Advance',
            filters: {
                status: 'Draft',
                employee: frm.doc.employee
            },
            fields: ['name']
        },
        function (ea_response) {
            let unclaimed_count = ea_response.length;
            checkMaxUnclaimedAndCreateEA(frm, unclaimed_count);
        }
    );
}

function checkMaxUnclaimedAndCreateEA(frm, unclaimed_count) {
    makeFrappeCall(
        'frappe.client.get_value',
        {
            doctype: 'Company',
            fieldname: ['max_unclaimed_ea', 'abbr'],
            filters: {
                name: frm.doc.company
            }
        },
        function (company_response) {
            let max_unclaimed_ea = company_response.max_unclaimed_ea;
            let company_abbr = company_response.abbr;

            if (unclaimed_count < max_unclaimed_ea) {
                createEmployeeAdvance(frm, company_abbr);
            } else {
                frappe.msgprint(__('The maximum number of unclaimed Employee Advances has been reached. Cannot create a new Employee Advance.'));
            }
        }
    );
}

function createEmployeeAdvance(frm, company_abbr) {
    let advance_account = "Employee Advances - " + company_abbr;

    makeFrappeCall(
        'frappe.client.insert',
        {
            doc: {
                doctype: 'Employee Advance',
                employee: frm.doc.employee,
                employee_name: frm.doc.employee_name,
                posting_date: frappe.datetime.nowdate(),
                purpose: frm.doc.purpose_of_travel,
                advance_amount: frm.doc.costings.reduce((total, costing) => total + costing.total_amount, 0),
                company: frm.doc.company,
                advance_account: advance_account,
                exchange_rate: 1,
                travel_request_ref: frm.doc.name,
            }
        },
        function (response) {
            if (response) {
                frm.set_value('employee_advance_ref', response.name);
                frm.save_or_update();

                frappe.set_route('Form', 'Employee Advance', response.name);
            }
        }
    );
}

function calculateTotalTravelCost(frm) {
    if (frm.doc.costings) {
        let total_travel_cost = frm.doc.costings.reduce((total, costing) => total + costing.total_amount, 0);
        frm.set_value('total_travel_cost', total_travel_cost);
    }
}
