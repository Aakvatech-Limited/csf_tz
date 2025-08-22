// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Workflow Transition History', {
    refresh: function(frm) {
        // Add button to view referenced document
        if(frm.doc.reference_doctype && frm.doc.reference_name) {
            frm.add_custom_button(__('Open Document'), function() {
                frappe.set_route('Form', frm.doc.reference_doctype, frm.doc.reference_name);
            });
        }
        
        // Add timeline button
        if(frm.doc.reference_doctype && frm.doc.reference_name) {
            frm.add_custom_button(__('View Timeline'), function() {
                frappe.route_options = {
                    "reference_doctype": frm.doc.reference_doctype,
                    "reference_name": frm.doc.reference_name
                };
                frappe.set_route('List', 'Workflow Transition History');
            });
        }
    },
    
    reference_doctype: function(frm) {
        // Clear reference name when doctype changes
        frm.set_value('reference_name', '');
    }
});

