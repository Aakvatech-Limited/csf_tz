frappe.require([
    '/assets/csf_tz/js/shortcuts.js'
]);

frappe.ui.form.on("Purchase Invoice", {
    // Budget check for Purchase Invoice is now handled server-side via doc_events hooks
    // See apps/csf_tz/csf_tz/hooks.py and apps/csf_tz/csf_tz/budget_check.py
    supplier: function(frm) {
        if (!frm.doc.supplier) {
            return
        }
        setTimeout(function() {
            if (!frm.doc.tax_category){
                frappe.call({
                    method: "csf_tz.custom_api.get_tax_category",
                    args: {
                        doc_type: frm.doc.doctype,
                        company: frm.doc.company,
                    },
                    callback: function(r) {
                        if(!r.exc) {
                            frm.set_value("tax_category", r.message);
                            frm.trigger("tax_category");
                        }
                    }
                });           
        }
          }, 1000);   
    },
    setup: function(frm) {
        frm.set_query("taxes_and_charges", function() {
			return {
				"filters": {
                    "company": frm.doc.company,
				}
			};
        });
        frappe.call({
            method: "erpnext.accounts.doctype.accounting_dimension.accounting_dimension.get_dimensions",
            callback: function(r) {
                if(!r.exc) {
                    const dimensions = [];
                    r.message[0].forEach(element => {
                        dimensions.push(element.fieldname);
                    });
                    frm.dimensions = dimensions;
                    // console.log(frm.dimensions);
                    
                }
            }
        });  
        // const dimensions_fields = $("div.frappe-control[data-fieldname='expense_type']")
        // console.log(dimensions_fields);
    },
    refresh: (frm) => {
        frappe.db.get_single_value("CSF TZ Settings", "limit_uom_as_item_uom").then(limit_uom_as_item_uom => {
            if (limit_uom_as_item_uom == 1) {
            frm.set_query("uom", "items", function (frm, cdt, cdn) {
                let row = locals[cdt][cdn];
                return {
                    query:
                        "erpnext.accounts.doctype.pricing_rule.pricing_rule.get_item_uoms",
                    filters: {
                        value: row.item_code,
                        apply_on: "Item Code",
                    },
                };
            });
            }
        });
        frm.trigger("add_write_off_button");
    },
    onload: function(frm){
        frm.dimensions.forEach(i => {
            let dimension_field = $(`div.frappe-control[data-fieldname='${i}']`).find("input");
            dimension_field.on("focusout",function() {
                frm.doc.items.forEach(row => {
                    row[i]=frm.doc[i];
                });
                frm.refresh_field("items");
            });
        });
    },

    // Write-off Journal Entry Feature
    add_write_off_button: function (frm) {
        // Check if feature is enabled and conditions are met
        frappe.db
            .get_single_value("CSF TZ Settings", "enable_write_off_jv_pe")
            .then((enable_write_off) => {
                if (enable_write_off &&
                    frm.doc.docstatus === 1 &&
                    frm.doc.outstanding_amount > 0 &&
                    !frm.doc.is_return) {

                    frm.add_custom_button(__("Write Off Outstanding"), function () {
                        // Fetch the write-off account from Company before showing the dialog
                        frappe.db.get_value("Company", frm.doc.company, "write_off_account").then(function(r) {
                            let write_off_account = r.message ? r.message.write_off_account : null;

                            // Show dialog to select write-off account
                            let dialog = new frappe.ui.Dialog({
                                title: __("Write Off Outstanding Amount"),
                                fields: [
                                    {
                                        fieldname: "write_off_account",
                                        label: __("Write Off Account"),
                                        fieldtype: "Link",
                                        options: "Account",
                                        "default": write_off_account,
                                        reqd: 1,
                                        get_query: function() {
                                            return {
                                                filters: {
                                                    "report_type": "Balance Sheet",
                                                    "is_group": 0,
                                                    "company": frm.doc.company
                                                }
                                            };
                                        }
                                    },
                                    {
                                        fieldname: "outstanding_amount",
                                        label: __("Outstanding Amount"),
                                        fieldtype: "Currency",
                                        default: frm.doc.outstanding_amount,
                                        read_only: 1
                                    }
                                ],
                                primary_action_label: __("Create Write Off Entry"),
                                primary_action: function(values) {
                                    frappe.call({
                                        method: "csf_tz.custom_api.create_write_off_jv_pi",
                                        args: {
                                            purchase_invoice: frm.doc.name,
                                            account: values.write_off_account
                                        },
                                        callback: function(r) {
                                            if (r.message) {
                                                frappe.msgprint(__("Write-off Journal Entry created: {0}", [r.message]));
                                                frm.reload_doc();
                                            }
                                        }
                                    });
                                    dialog.hide();
                                }
                            });
                            dialog.show();
                        });
                    }, __("Create"));
                }
            });
    },

});
frappe.ui.form.on("Purchase Invoice Item", {
    items_add: function(frm, cdt, cdn) {
        var row = frappe.get_doc(cdt, cdn);
        frm.dimensions.forEach(i => {
            row[i]=frm.doc[i];
        });
        frm.refresh_field("items");
    },
    csf_tz_create_wtax_entry: (frm, cdt, cdn) => {
        frappe.call('csf_tz.custom_api.make_withholding_tax_gl_entries_for_purchase', {
            doc: frm.doc, method: 'From Front End'
        }).then(r => {
            frm.refresh();
        });
    }
});