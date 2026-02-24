// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.ui.form.on('TRA TAX Inv', {
    refresh: function (frm) {
        // Add Create Invoice button if document is saved and no invoice exists yet
        if (frm.doc.name && !frm.doc.reference_docname) {
            frm.add_custom_button(__('Create Invoice'), function () {
                show_invoice_type_dialog(frm);
            }, __('Actions'));
        }

        // Show reference invoice link if exists
        if (frm.doc.reference_docname && frm.doc.reference_doctype) {
            frm.add_custom_button(__('View ' + frm.doc.reference_doctype), function () {
                frappe.set_route('Form', frm.doc.reference_doctype, frm.doc.reference_docname);
            }, __('Actions'));
        }
    },
});

function show_invoice_type_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Create Invoice'),
        fields: [
            {
                fieldtype: 'Select',
                fieldname: 'invoice_type',
                label: __('Invoice Type'),
                options: [
                    { label: __('Purchase Invoice'), value: 'Purchase Invoice' },
                    { label: __('Sales Invoice'), value: 'Sales Invoice' }
                ],
                reqd: 1,
                description: __('Select the type of invoice to create from this TRA Tax Invoice')
            },
            {
                fieldtype: 'HTML',
                fieldname: 'info_html',
                options: `
                    <div class="alert alert-info">
                        <strong>Note:</strong>
                        <ul>
                            <li><strong>Purchase Invoice:</strong> Use when this TRA receipt represents a purchase made by your company</li>
                            <li><strong>Sales Invoice:</strong> Use when this TRA receipt represents a sale made by your company</li>
                        </ul>
                        <p>The system will validate that all required master records (Items, Customer/Supplier) exist before creating the invoice.</p>
                    </div>
                `
            }
        ],
        primary_action_label: __('Create Invoice'),
        primary_action: function (values) {
            if (!values.invoice_type) {
                frappe.msgprint(__('Please select an invoice type'));
                return;
            }

            dialog.hide();
            create_invoice_from_tra_tax_inv(frm, values.invoice_type);
        }
    });

    dialog.show();
}

function create_invoice_from_tra_tax_inv(frm, invoice_type) {
    frappe.show_progress(__('Creating Invoice'), 50, 100, __('Validating data...'));

    frappe.call({
        method: 'csf_tz.csf_tz.doctype.tra_tax_inv.tra_tax_inv.create_invoice_from_tra_tax_inv',
        args: {
            tra_tax_inv_name: frm.doc.name,
            invoice_type: invoice_type
        },
        callback: function (response) {
            frappe.hide_progress();

            if (response.message && response.message.success) {
                frappe.show_alert({
                    message: __(response.message.message),
                    indicator: 'green'
                });

                // Refresh the form to show the reference
                frm.reload_doc();

                // Ask if user wants to open the created invoice
                frappe.confirm(
                    __('Invoice created successfully. Do you want to open the {0}?', [response.message.invoice_type]),
                    function () {
                        frappe.set_route('Form', response.message.invoice_type, response.message.invoice_name);
                    }
                );
            } else {
                let error_message = response.message ? response.message.message : __('Unknown error occurred');
                frappe.msgprint({
                    title: __('Error Creating Invoice'),
                    message: error_message,
                    indicator: 'red'
                });
            }
        },
        error: function (error) {
            frappe.hide_progress();
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to create invoice. Please try again.'),
                indicator: 'red'
            });
            console.error('Error creating invoice:', error);
        }
    });
}
