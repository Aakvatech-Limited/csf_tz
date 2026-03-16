frappe.ui.form.on("Customer", {
    vfd_cust_id_type: function (frm) {
        if (frm.doc.vfd_cust_id_type == "1- TIN") {
            let tax_id = frm.doc.tax_id;
            let vfd_cust_id = tax_id.split('-').join('');
            frm.set_value("vfd_cust_id", vfd_cust_id)
        }
    },
    vfd_cust_id: function (frm) {
        // frappe.msgprint(string(frm.doc.vfd_cust_id.length))
        // frappe.msgprint(frm.doc.vfd_cust_id_type.startsWith('1'))
        if (frm.doc.tax_id.length != 9 && frm.doc.vfd_cust_id_type.startsWith('1')) {
            frappe.throw(__("TIN Number is should be 9 numbers only, Please remove the dashes"));
        }
    },
    tax_id: function (frm) {
        frm.fields_dict.tax_id.$input.focusout(function () {
            if (frm.doc.tax_id.length != 9) {
                frappe.throw(__("TIN Number is should be 9 numbers only, Please remove the dashes"));
            }
            if (frm.doc.tax_id) {
                let tax_id = frm.doc.tax_id;
                let vfd_cust_id = tax_id.split('-').join('');
                frm.set_value("vfd_cust_id", vfd_cust_id);
                frm.set_value("vfd_cust_id_type", "1- TIN");
            }
        });
    },
})