frappe.require([
    '/assets/csf_tz/js/shortcuts.js'
]);

frappe.ui.form.on("Material Request", {
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
});


frappe.ui.keys.add_shortcut({
    shortcut: 'ctrl+q',
    action: () => {
        ctrlQ("Material Request Item");
    },
    page: this.page,
    description: __('Select Item Warehouse'),
    ignore_inputs: true,
});
