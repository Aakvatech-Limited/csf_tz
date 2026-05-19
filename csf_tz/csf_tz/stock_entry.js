frappe.ui.form.on("Stock Entry", {
    setup: function (frm) {
        frm.trigger("set_warehouse_options");
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
    onload: function (frm) {
        if (frm.docstatus == 0) {
            frm.trigger("stock_entry_type");
            frm.trigger("set_warehouse_options");
        }
    },
    company: function (frm) {
        frm.trigger("set_warehouse_options");
    },
    stock_entry_type: function (frm) {
        if (frm.doc.stock_entry_type != "Repack from template") {
            frappe.meta.get_docfield("Stock Entry Detail", "item_code", frm.doc.name).read_only = 0;
            frappe.meta.get_docfield("Stock Entry Detail", "item_group", frm.doc.name).read_only = 0;
            $('.grid-add-multiple-rows').show();
            $('.grid-add-row').show();
            $('.grid-remove-rows').show();
            $('.grid-download').show();
            $('.grid-upload').show();
            frm.toggle_reqd("qty", 0);
        }
        if (["Repack from template", "Manufacture"].includes(frm.doc.stock_entry_type)) {
            frm.set_df_property('total_net_weight', 'hidden', 1)
        }
        else {
            frm.set_df_property('total_net_weight', 'hidden', 0)
        }
        frm.refresh_field("items");
        frm.refresh();
    },
    calculate_net_weight: function (frm) {
        frm.doc.total_net_weight = 0.0;

        $.each(frm.doc["items"] || [], function (i, item) {
            frm.doc.total_net_weight += flt(item.total_weight);
        });
        refresh_field("total_net_weight");
    },
    set_warehouse_options: function (frm) {
        frappe.call({
            "method": "csf_tz.custom_api.get_warehouse_options",
            "args": { company: frm.doc.company },
            callback: function (r) {
                if (r.message && r.message.length) {
                    // frappe.meta.get_docfield("ModulesT", "module", frm.doc.name).options = r.message;
                    // frm.get_docfield("taxes", "rate").reqd = 0;
                    frm.set_df_property("final_destination", "options", r.message);
                }
            }
        });
    },
});

frappe.ui.form.on("Stock Entry Detail", {
    conversion_factor: function (frm, cdt, cdn) {
        var item = frappe.get_doc(cdt, cdn);
        item.total_weight = flt(item.transfer_qty * item.weight_per_unit * item.conversion_factor);
        refresh_field("total_weight");
        frm.trigger("calculate_net_weight");
    },
    qty: function (frm, cdt, cdn) {
        frm.script_manager.trigger("conversion_factor", cdt, cdn);
    },
});
