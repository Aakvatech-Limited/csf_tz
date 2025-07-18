frappe.require([
    '/assets/csf_tz/js/shortcuts.js'
]);

frappe.ui.form.on("Purchase Invoice", {
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