frappe.ui.form.on('Employee', {
    generate_contact_qr: function(frm) {
        frappe.call({
            method: 'csf_tz.csftz_hooks.employee_contact_qr.generate_contact_qr',
            args: {
                employee: frm.doc.name
            },
            callback: function(r) {
                if (r.message) {
                    let d = new frappe.ui.Dialog({
                        title: __('Employee Contact QR Code'),
                        fields: [{
                            label: 'QR Code',
                            fieldtype: 'HTML',
                            fieldname: 'qr_display',
                            options: `<div style="text-align: center;">
                                <img src="data:image/png;base64,${r.message}" />
                                <p>Scan this QR code to add contact</p>
                            </div>`
                        }]
                    });
                    d.show();
                }
            }
        });
    }
});