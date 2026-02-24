// Copyright (c) 2025, Aakvatech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Foreign Import Transaction', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.status !== 'Completed') {
            frm.add_custom_button(__('Recalculate Differences'), function() {
                frappe.call({
                    method: 'recalculate_differences',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(__('Exchange differences recalculated successfully'));
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
        
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('View Exchange Report'), function() {
                frappe.route_options = {
                    "purchase_invoice": frm.doc.purchase_invoice,
                    "supplier": frm.doc.supplier
                };
                frappe.set_route("query-report", "Import Exchange Differences");
            });

            // Add debugging button
            frm.add_custom_button(__('Debug Payment Linking'), function() {
                let payment_entry = prompt(__('Enter Payment Entry name to debug:'));
                if (payment_entry) {
                    frappe.call({
                        method: 'csf_tz.csftz_hooks.exchange_calculations.debug_payment_linking_issue',
                        args: {
                            payment_entry_name: payment_entry
                        },
                        callback: function(r) {
                            if (r.message && !r.message.error) {
                                let debug_info = r.message;
                                let msg = `<h4>Payment Details:</h4>
                                    <ul>
                                        <li><strong>Payment Type:</strong> ${debug_info.payment_details.payment_type}</li>
                                        <li><strong>Party Type:</strong> ${debug_info.payment_details.party_type}</li>
                                        <li><strong>Party:</strong> ${debug_info.payment_details.party}</li>
                                        <li><strong>Currency:</strong> ${debug_info.payment_details.paid_to_account_currency}</li>
                                        <li><strong>Exchange Rate:</strong> ${debug_info.payment_details.source_exchange_rate}</li>
                                        <li><strong>Amount:</strong> ${debug_info.payment_details.paid_amount}</li>
                                        <li><strong>Status:</strong> ${debug_info.payment_details.docstatus == 1 ? 'Submitted' : 'Draft'}</li>
                                    </ul>`;

                                if (debug_info.issues.length > 0) {
                                    msg += `<h4 style="color: red;">Issues Found:</h4><ul>`;
                                    debug_info.issues.forEach(issue => {
                                        msg += `<li style="color: red;">${issue}</li>`;
                                    });
                                    msg += `</ul>`;
                                }

                                if (debug_info.potential_trackers.length > 0) {
                                    msg += `<h4>Potential Trackers:</h4>`;
                                    debug_info.potential_trackers.forEach(tracker => {
                                        let color = tracker.issues.length > 0 ? 'red' : 'green';
                                        msg += `<div style="border: 1px solid #ddd; padding: 10px; margin: 5px;">
                                            <strong>${tracker.name}</strong> (${tracker.purchase_invoice})<br>
                                            Currency: ${tracker.currency} | Status: ${tracker.status}<br>
                                            Currency Match: ${tracker.currency_match ? '✅' : '❌'} |
                                            Status OK: ${tracker.status_ok ? '✅' : '❌'}`;
                                        if (tracker.issues.length > 0) {
                                            msg += `<br><span style="color: red;">Issues: ${tracker.issues.join(', ')}</span>`;
                                        }
                                        msg += `</div>`;
                                    });
                                } else {
                                    msg += `<p style="color: orange;">No trackers found for supplier: ${debug_info.payment_details.party}</p>`;
                                }

                                frappe.msgprint({
                                    title: __('Payment Linking Debug Info'),
                                    message: msg,
                                    indicator: 'blue'
                                });
                            } else if (r.message && r.message.error) {
                                frappe.msgprint(`Error: ${r.message.error}`, 'Error');
                            }
                        }
                    });
                }
            }, __('Debug'));

            // Add manual linking button
            frm.add_custom_button(__('Link Payment Manually'), function() {
                let payment_entry = prompt(__('Enter Payment Entry name to link:'));
                if (payment_entry) {
                    frappe.call({
                        method: 'csf_tz.csftz_hooks.exchange_calculations.manually_link_payment_to_tracker',
                        args: {
                            payment_entry_name: payment_entry,
                            tracker_name: frm.doc.name
                        },
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.msgprint(r.message.success, 'Success');
                                frm.reload_doc();
                            } else if (r.message && r.message.error) {
                                frappe.msgprint(`Error: ${r.message.error}`, 'Error');
                            }
                        }
                    });
                }
            }, __('Debug'));
        }
        
        // Set color indicator based on status
        if (frm.doc.status && frm.dashboard) {
            let color = {
                'Draft': 'orange',
                'Active': 'blue',
                'Completed': 'green',
                'Cancelled': 'red'
            }[frm.doc.status];

            // Use the correct method for setting indicators
            if (frm.dashboard.add_indicator) {
                frm.dashboard.add_indicator(__('Status: {0}', [frm.doc.status]), color);
            }
        }

        // Show total differences summary
        if (frm.doc.total_gain_loss && frm.dashboard && frm.dashboard.add_indicator) {
            let message = frm.doc.total_gain_loss >= 0 ?
                __('Total Exchange Gain: {0}', [format_currency(frm.doc.total_gain_loss)]) :
                __('Total Exchange Loss: {0}', [format_currency(Math.abs(frm.doc.total_gain_loss))]);

            frm.dashboard.add_indicator(message, frm.doc.total_gain_loss >= 0 ? 'green' : 'red');
        }
    },
    
    purchase_invoice: function(frm) {
        if (frm.doc.purchase_invoice) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Purchase Invoice',
                    name: frm.doc.purchase_invoice
                },
                callback: function(r) {
                    if (r.message) {
                        let pi = r.message;
                        
                        // Check if it's a foreign currency invoice
                        frappe.db.get_value('Company', pi.company, 'default_currency')
                        .then(result => {
                            if (pi.currency === result.message.default_currency) {
                                frappe.msgprint(__('Selected Purchase Invoice is not in foreign currency'));
                                frm.set_value('purchase_invoice', '');
                                return;
                            }
                            
                            // Set fields from PI
                            frm.set_value({
                                'supplier': pi.supplier,
                                'transaction_date': pi.posting_date,
                                'currency': pi.currency,
                                'original_exchange_rate': pi.conversion_rate,
                                'invoice_amount_foreign': pi.grand_total,
                                'invoice_amount_base': pi.base_grand_total,
                                'company': pi.company
                            });
                        });
                    }
                }
            });
        }
    }
});

frappe.ui.form.on('Foreign Import Payment Details', {
    payment_entry: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.payment_entry) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Payment Entry',
                    name: row.payment_entry
                },
                callback: function(r) {
                    if (r.message) {
                        let pe = r.message;
                        frappe.model.set_value(cdt, cdn, {
                            'payment_date': pe.posting_date,
                            'payment_amount_foreign': pe.paid_amount,
                            'payment_amount_base': pe.base_paid_amount,
                            'payment_exchange_rate': pe.source_exchange_rate
                        });
                        
                        // Calculate exchange difference
                        let original_rate = flt(frm.doc.original_exchange_rate);
                        let payment_rate = flt(pe.source_exchange_rate);
                        let paid_amount = flt(pe.paid_amount);
                        
                        if (original_rate !== payment_rate) {
                            let exchange_diff = paid_amount * (payment_rate - original_rate);
                            frappe.model.set_value(cdt, cdn, 'exchange_difference', exchange_diff);
                        }
                    }
                }
            });
        }
    }
});
