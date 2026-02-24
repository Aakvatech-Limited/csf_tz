// Copyright (c) 2023, Aakvatech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inter Company Stock Transfer', {
    refresh: function (frm) {
        frm.set_query('default_from_warehouse', () => {
            return {
                filters: {
                    company: frm.doc.from_company
                }
            };
        });
        frm.set_query('default_to_warehouse', () => {
            return {
                filters: {
                    company: frm.doc.to_company
                }
            };
        });
        frm.fields_dict['items_child'].grid.get_field('batch_no').get_query = function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            return {
                filters: {
                    item_name: row.item_name
                }
            };
        };
    }
});

