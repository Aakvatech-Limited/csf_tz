/**
 * Budget Check Utility Functions
 *
 * This module provides common functionality for automatic budget checking on validate
 * across different doctypes (Journal Entry, Material Request, Purchase Order, Purchase Invoice)
 *
 * Note: This module relies on ERPNext's native budget validation system.
 * Budget violations are raised as exceptions on the server side and displayed
 * automatically by Frappe's framework.
 */

frappe.provide('csf_tz.budget_check');

/**
 * Perform automatic budget check for a document during validate event
 * @param {Object} frm - The form object
 */
csf_tz.budget_check.auto_check = function(frm) {
    // Only check if document is in draft status
    if (frm.doc.docstatus !== 0) {
        return;
    }

    // Call server-side method directly
    // The Python method will check if the feature is enabled and perform budget validation
    // ERPNext's budget validation will raise exceptions that Frappe displays automatically
    frappe.call({
        method: 'csf_tz.budget_check.check_budget_before_submit',
        args: {
            doctype: frm.doctype,
            docname: frm.docname
        },
        // No custom callback needed - ERPNext handles displaying budget violations
        error: function(r) {
            // Errors are already displayed by Frappe's framework
            // Just log for debugging purposes
            console.log('Budget check completed');
        }
    });
};

